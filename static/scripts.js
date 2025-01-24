document.addEventListener("DOMContentLoaded", function () {
    const loadingIndicator = document.getElementById("loading-indicator");
  
    window.addEventListener("beforeunload", function () {
      loadingIndicator.style.display = "block";
    });
  
    window.addEventListener("load", function () {
      loadingIndicator.style.display = "none";
    });
  });
  

function updateFileName() {
    const fileInput = document.getElementById('fileInput');
    const fileNameDisplay = document.getElementById('fileName');
    
    if (fileInput.files.length > 0) {
        const fileNames = Array.from(fileInput.files).map(file => file.name).join(', ');
        fileNameDisplay.textContent = fileNames;
    } else {
        fileNameDisplay.textContent = 'No files chosen';
    }
}

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
    console.log("HANDLE MODEL")
    const modelSelect = document.getElementById("modelSelect")
    const apiKeyInput = document.getElementById("apiKeyInput");
    const urlInput = document.getElementById("urlInput");

    // // Reset both boxes first
    // apiKeyBox.style.display = "none";
    // baseUrlBox.style.display = "none";

    if (modelSelect.value === "Local") {
        apiKeyInput.style.display = "block";
        urlInput.style.display = "block";
    } else {
        apiKeyInput.style.display = "block";
        urlInput.style.display = "block";
    }
}

function sendLLM() {

    console.log("sendData function called");

    const llm = document.getElementById("modelSelect").value;
    const api_key = document.getElementById("apiKeyInput").value;
    const base_url = document.getElementById("urlInput").value;
    let llm_type;

    if (api_key) {
        llm_type = "Cloud";
    }
    else {
        llm_type = "Local";
    }


    const arguments = {
        llm: llm,
        llm_type: llm_type,
        api_key: api_key,
        base_url: base_url
    };

    console.log("Arguments:", arguments)

    // Send data to the API
    fetch("/llm_setup", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(arguments)
    })
    .then(response => {
        if (response.ok) {
            alert("Data submitted successfully!");
        } else {
            alert("Failed to submit data.");
        }
    })
    .catch(error => {
        console.error("Error:", error);
        alert("An error occurred.");
    });

}

function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

function toggleMenu(event, group_id) {
    event.stopPropagation(); // Prevent the click from bubbling to the parent item

    const menu = document.getElementById('menu-' + group_id);

    // Toggle the visibility of the menu
    menu.style.display = (menu.style.display === 'block') ? 'none' : 'block';

    // Close the menu when clicking anywhere outside
    window.addEventListener('click', function closeMenu(e) {
        if (!menu.contains(e.target) && !event.target.contains(e.target)) {
            menu.style.display = 'none';
            window.removeEventListener('click', closeMenu);
        }
    });
}



document.addEventListener("DOMContentLoaded", () => {
    const sections = document.querySelectorAll(".chat-sections > div");
    const container = document.querySelector(".chat-container");

    sections.forEach((section) => {
        section.addEventListener("click", (e) => {
            // Remove 'expanded' class from all sections
            sections.forEach((sec) => sec.classList.remove("expanded"));

            // Add 'expanded' class to the clicked section
            section.classList.add("expanded");

            // Stop click event propagation to prevent triggering the container click listener
            e.stopPropagation();
        });
    });

    // Listen for clicks outside any section
    container.addEventListener("click", () => {
        sections.forEach((sec) => sec.classList.remove("expanded"));
    });
});





// go to api endpoint for analyzing the group of PCAPs

async function runAnalysis(group_id, llm) {
    
    console.log("RUNNNNING")

    if (llm === "No LLM Selected. Must pick one before Analysis" ) {
        alert("Must Select an LLM before Analysis");
        window.location.href = '/';
    }
    else {
        group_id = Number(group_id)

        console.log("TYP", typeof group_id);
    
        window.location.href = `/run_analysis?group_id=${group_id}`;
    }

}

async function editGroup(event, group_id) {
    
    event.stopPropagation();

    group_id = Number(group_id)

    console.log("EDIT", typeof group_id);

    window.location.href = `/edit_group?group_id=${group_id}`;
}

async function deletePCAP(group_id, group_path, pcap) {
    // Example: Send data to the server

    group_id = Number(group_id)
    console.log("HELLO DELETE")

    fetch(`/delete_pcap?group_id=${group_id}&group_path=${encodeURIComponent(group_path)}&pcap=${pcap}`, {
        method: 'DELETE',
    }).then(response => {
        if (response.ok) {
            // Handle successful deletion
            window.location.href = `/edit_group?group_id=${group_id}`;  // Use the URL returned by the server
        } else {
            // Handle error
            alert('Error deleting group');
        }
    });

}

async function goToChat(groupPath) {
    const response = await fetch(`/chat_bot?group=${groupPath}`);
    if (response.redirected) {
        window.location.href = response.url;
    }
}

async function deleteGroup(event, group_id) {

    event.stopPropagation();

    group_id = Number(group_id)

    fetch(`/delete_group?group_id=${group_id}`, {
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