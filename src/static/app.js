document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const teacherOnlyNotice = document.getElementById("teacher-only-notice");
  const messageDiv = document.getElementById("message");
  const accountButton = document.getElementById("account-button");
  const accountPanel = document.getElementById("account-panel");
  const accountStatus = document.getElementById("account-status");
  const loginButton = document.getElementById("login-button");
  const logoutButton = document.getElementById("logout-button");
  const loginDialog = document.getElementById("login-dialog");
  const loginForm = document.getElementById("login-form");
  const cancelLoginButton = document.getElementById("cancel-login");
  let isTeacher = false;

  function showMessage(message, className) {
    messageDiv.textContent = message;
    messageDiv.className = className;
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  async function updateAuthStatus() {
    const response = await fetch("/auth/status");
    if (!response.ok) {
      throw new Error("Failed to check teacher login status");
    }
    const status = await response.json();
    isTeacher = status.authenticated;
    signupForm.classList.toggle("hidden", !isTeacher);
    teacherOnlyNotice.classList.toggle("hidden", isTeacher);
    loginButton.classList.toggle("hidden", isTeacher);
    logoutButton.classList.toggle("hidden", !isTeacher);
    accountStatus.textContent = isTeacher ? "Teacher signed in" : "Not signed in";
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) {
        throw new Error("Failed to load activities");
      }
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.replaceChildren(activitySelect.options[0]);

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft =
          details.max_participants - details.participants.length;
        const title = document.createElement("h4");
        title.textContent = name;
        const description = document.createElement("p");
        description.textContent = details.description;
        const schedule = document.createElement("p");
        schedule.innerHTML = `<strong>Schedule:</strong> ${escapeHTML(details.schedule)}`;
        const availability = document.createElement("p");
        availability.innerHTML = `<strong>Availability:</strong> ${spotsLeft} spots left`;
        activityCard.append(title, description, schedule, availability);

        const participants = document.createElement("div");
        participants.className = "participants-container";
        if (details.participants.length > 0) {
          const participantsTitle = document.createElement("h5");
          participantsTitle.textContent = "Participants:";
          const list = document.createElement("ul");
          list.className = "participants-list";
          details.participants.forEach((email) => {
            const item = document.createElement("li");
            const participantEmail = document.createElement("span");
            participantEmail.className = "participant-email";
            participantEmail.textContent = email;
            item.appendChild(participantEmail);
            if (isTeacher) {
              const unregisterButton = document.createElement("button");
              unregisterButton.className = "delete-btn";
              unregisterButton.type = "button";
              unregisterButton.textContent = "Remove";
              unregisterButton.setAttribute("aria-label", `Unregister ${email}`);
              unregisterButton.addEventListener("click", () =>
                handleUnregister(name, email)
              );
              item.appendChild(unregisterButton);
            }
            list.appendChild(item);
          });
          participants.append(participantsTitle, list);
        } else {
          const empty = document.createElement("p");
          empty.innerHTML = "<em>No participants yet</em>";
          participants.appendChild(empty);
        }
        activityCard.appendChild(participants);

        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  function escapeHTML(value) {
    return String(value).replace(/[&<>"']/g, (character) => {
      const entities = {
        "&": "&amp;",
        "<": "&lt;",
        ">": "&gt;",
        '"': "&quot;",
        "'": "&#39;",
      };
      return entities[character];
    });
  }

  async function handleUnregister(activity, email) {
    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to unregister. Please try again.", "error");
      console.error("Error unregistering:", error);
    }
  }

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        showMessage(result.message, "success");
        signupForm.reset();
        await fetchActivities();
      } else {
        showMessage(result.detail || "An error occurred", "error");
      }
    } catch (error) {
      showMessage("Failed to sign up. Please try again.", "error");
      console.error("Error signing up:", error);
    }
  });

  accountButton.addEventListener("click", () => {
    const isExpanded = accountButton.getAttribute("aria-expanded") === "true";
    accountButton.setAttribute("aria-expanded", String(!isExpanded));
    accountPanel.classList.toggle("hidden", isExpanded);
  });

  loginButton.addEventListener("click", () => {
    accountPanel.classList.add("hidden");
    accountButton.setAttribute("aria-expanded", "false");
    loginDialog.showModal();
  });

  cancelLoginButton.addEventListener("click", () => loginDialog.close());

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const formData = new FormData(loginForm);
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          username: formData.get("username"),
          password: formData.get("password"),
        }),
      });
      const result = await response.json();
      if (!response.ok) {
        showMessage(result.detail || "Unable to sign in.", "error");
        return;
      }
      loginForm.reset();
      loginDialog.close();
      await updateAuthStatus();
      await fetchActivities();
      showMessage(result.message, "success");
    } catch (error) {
      showMessage("Failed to sign in. Please try again.", "error");
      console.error("Error signing in:", error);
    }
  });

  logoutButton.addEventListener("click", async () => {
    try {
      const response = await fetch("/auth/logout", { method: "POST" });
      if (!response.ok) {
        throw new Error("Failed to sign out");
      }
      await updateAuthStatus();
      await fetchActivities();
      accountPanel.classList.add("hidden");
      accountButton.setAttribute("aria-expanded", "false");
      showMessage("Signed out successfully", "success");
    } catch (error) {
      showMessage("Failed to sign out. Please try again.", "error");
      console.error("Error signing out:", error);
    }
  });

  async function initialize() {
    try {
      await updateAuthStatus();
      await fetchActivities();
    } catch (error) {
      showMessage("Unable to initialize teacher controls.", "error");
      console.error("Error initializing app:", error);
    }
  }

  initialize();
});
