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

document.addEventListener("DOMContentLoaded", function () {
    handleModel(); // Ensure the correct input is shown on page load
});

// Function to show or hide the input fields based on dropdown selection
function handleModel() {
    const modelSelect = document.getElementById("modelSelect")
    const apiKeyInput = document.getElementById("apiKeyInput");
    const urlInput = document.getElementById("urlInput");

    // // Reset both boxes first
    // apiKeyBox.style.display = "none";
    // baseUrlBox.style.display = "none";

    if (modelSelect.value === "Local") {
        apiKeyInput.style.display = "none";
        urlInput.style.display = "block";
    } else {
        apiKeyInput.style.display = "block";
        urlInput.style.display = "none";
    }
}

// go to api endpoint for analyzing the group of PCAPs
async function runAnalysis(groupPath) {
    const response = await fetch(`/run_analysis?group=${groupPath}`);
    if (response.redirected) {
        window.location.href = response.url;
    }
}

async function goToChat(groupPath) {
    const response = await fetch(`/chat_bot?group=${groupPath}`);
    if (response.redirected) {
        window.location.href = response.url;
    }
}

function deleteGroup() {
    const form = document.getElementById('deleteGroupForm');
    const groupId = form.elements['group_id'].value;
    const group = form.elements['group'].value;
    fetch(`/delete_group?group_id=${groupId}&group=${encodeURIComponent(group)}`, {
        method: 'DELETE',
    }).then(response => {
        if (response.ok) {
            // Handle successful deletion
            window.location.href = "/";  // Use the URL returned by the server
        } else {
            // Handle error
            alert('Error deleting group');
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    const checkboxes = document.querySelectorAll(".item-checkbox");
    const deleteBtn = document.getElementById("delete-button");

    // Show the delete button if at least one item is checked
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener("change", () => {
            const selected = Array.from(checkboxes).some(cb => cb.checked);

            console.log("Checkbox selected:", selected); // Debugging line
            deleteBtn.style.display = selected ? "block" : "none";

            console.log("Delete button style:", deleteBtn.style.display); // Debugging line

        });
    });
});

function deleteSelectedItems() {
    const checkboxes = document.querySelectorAll(".item-checkbox");
    const selectedItems = Array.from(checkboxes)
        .filter(cb => cb.checked)
        .map(cb => cb.value);

    // Define other variables to send to the endpoint
    const deleteBtn = document.getElementById("delete-button")
    const group = deleteBtn.getAttribute("group")
    const group_id = deleteBtn.getAttribute("group_id")

    const params = new URLSearchParams();
    selectedItems.forEach(pcap => params.append("pcaps", pcap));
    params.append("group", group);
    params.append("group_id", group_id);

    // Send DELETE request with query parameters
    fetch(`/delete_items?${params.toString()}`, {
        method: "DELETE",
    })
    .then(response => response.json())
    .then(data => {
        console.log("Success:", data);
        const apiUrl = `/group_interface?group=${encodeURIComponent(group)}&group_id=${encodeURIComponent(group_id)}`;
        window.location.href = apiUrl;
    })
    .catch(error => {
        console.error("Error:", error);
    });
}


// document.addEventListener("DOMContentLoaded", function () {
//     const modelSelect = document.getElementById('model');
//     const urlInput = document.querySelector('input[name="url"]');
//     const apiKeyInput = document.querySelector('input[name="api_key"]');
    
//     // Function to toggle input visibility based on selected model
//     modelSelect.addEventListener('change', function () {
//         if (modelSelect.value === 'Local') {
//             urlInput.style.display = 'block';
//             apiKeyInput.style.display = 'none';
//         } else if (modelSelect.value === 'Mistral' || modelSelect.value === 'OpenAI') {
//             apiKeyInput.style.display = 'block';
//             urlInput.style.display = 'none';
//         }
//     });

//     // Trigger change on load in case the model is pre-selected
//     modelSelect.dispatchEvent(new Event('change'));
// });