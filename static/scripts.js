async function uploadFiles() {
    const formData = new FormData();
    formData.append("groupfolder", document.getElementById("groupfolder"));

    for (const file of document.getElementById("files").files) {
        formData.append("files", file)
    }

    const response = await fetch("/upload", {
        method: "POST",
        body: formData
    });

    if (response.redirected) {
        window.location.href = response.url;
    } else {
        const message = await response.text();
        alert(message);
    }
}

async function navigateToFiles() {
    const response = await fetch("/show_groups");
    const data = await response.json();

    const groupList = document.getElementById("group-links");
    groupList.innerHTML = "";
    data.groups.forEach(group => {
        const listItem = document.createElement("li");
        listItem.innerHTML = `<a href="#" onclick="runAnalysis('${group.path}')">${group.name}</a>`;
    });

    document.getElementById("welcome-form").style.display = "none";
    document.getElementById("group-list").style.display = "block";
}

// go to api endpoint for analyzing the group of PCAPs
async function runAnalysis(groupPath) {
    const response = await fetch(`/run_analysis?group=${groupPath}`);
    if (response.redirected) {
        window.location.href = response.url;
    }
}

async function sendMessage() {
    const formData = new FormData();
    formData.append("user_input", document.getElementById("user-input").value);

    const response = await fetch("/chat_bot", {
        method: "POST",
        body: formData,
    });

    const data = await response.text();
    document.getElementById("chat-box").innerHTML = data;
    document.getElementById("user-input").value = "";
}

function goHome() {
    document.getElementById("group-list").style.display = "none";
    document.getElementById("welcome-form").style.display = "block";
    document.getElementById("chat-box").style.display = "none";
}

// Function to show or hide the input fields based on dropdown selection
function handleModel() {
    const selectedOption = document.getElementById("api-dropdown").value;
    const apiKeyBox = document.getElementById("api-key-box");
    const baseUrlBox = document.getElementById("base-url-box");

    // Reset both boxes first
    apiKeyBox.style.display = "none";
    baseUrlBox.style.display = "none";

    // Show the corresponding text box based on the selection
    if (selectedOption === "Mistral" || selectedOption === "OpenAI") {
        apiKeyBox.style.display = "block";  // Show API Key text box
    } else if (selectedOption === "Local") {
        baseUrlBox.style.display = "block"; // Show Base URL text box
    }
}

document.addEventListener("DOMContentLoaded", function () {
    const modelSelect = document.getElementById('model');
    const urlInput = document.querySelector('input[name="url"]');
    const apiKeyInput = document.querySelector('input[name="api_key"]');
    
    // Function to toggle input visibility based on selected model
    modelSelect.addEventListener('change', function () {
        if (modelSelect.value === 'Local') {
            urlInput.style.display = 'block';
            apiKeyInput.style.display = 'none';
        } else if (modelSelect.value === 'Cloud') {
            apiKeyInput.style.display = 'block';
            urlInput.style.display = 'none';
        }
    });

    // Trigger change on load in case the model is pre-selected
    modelSelect.dispatchEvent(new Event('change'));
});