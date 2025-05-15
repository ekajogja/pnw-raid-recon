
document.addEventListener('DOMContentLoaded', function() {
    const passwordGate = document.getElementById('password-gate');
    const passwordInput = document.getElementById('password-input');
    const passwordSubmit = document.getElementById('password-submit');
    const passwordError = document.getElementById('password-error');
    const mainContent = document.getElementById('main-content');
    const apiKeyInput = document.getElementById('api-key-input');
    const scanForm = document.querySelector('form');
    const apiKeyHiddenInput = document.getElementById('api_key_hidden'); // Hidden input for API key

    const correctPassword = "Hail Shogun!"; // The required password

    // Check if password is already stored in local storage (optional persistence)
    const storedPassword = localStorage.getItem('pnw_raid_scanner_password');
    if (storedPassword === correctPassword) {
        passwordGate.style.display = 'none';
        mainContent.style.display = 'block';
        loadApiKey(); // Load API key if password is correct
    } else {
        passwordGate.style.display = 'flex'; // Use flex to center content
        mainContent.style.display = 'none';
    }

    // Password submit button event listener
    if (passwordSubmit) {
        passwordSubmit.addEventListener('click', function() {
            if (passwordInput.value === correctPassword) {
                passwordGate.style.display = 'none';
                mainContent.style.display = 'block';
                passwordError.style.display = 'none';
                localStorage.setItem('pnw_raid_scanner_password', correctPassword); // Store password (optional)
                loadApiKey(); // Load API key after successful login
            } else {
                passwordError.style.display = 'block';
            }
        });
    }

    // Allow submitting password with Enter key
    if (passwordInput) {
        passwordInput.addEventListener('keypress', function(event) {
            if (event.key === 'Enter') {
                event.preventDefault();
                passwordSubmit.click();
            }
        });
    }

    // Load API key from local storage
    function loadApiKey() {
        const storedApiKey = localStorage.getItem('pnw_api_key');
        if (apiKeyInput && storedApiKey) {
            apiKeyInput.value = storedApiKey;
            if (apiKeyHiddenInput) {
                apiKeyHiddenInput.value = storedApiKey; // Set hidden input value
            }
        }
    }

    // Save API key to local storage when input changes
    if (apiKeyInput) {
        apiKeyInput.addEventListener('input', function() {
            localStorage.setItem('pnw_api_key', apiKeyInput.value);
            if (apiKeyHiddenInput) {
                apiKeyHiddenInput.value = apiKeyInput.value; // Update hidden input value
            }
        });
    }

    // Handle form submission with loading state and add API key to form data
    if (scanForm) {
        scanForm.addEventListener('submit', function(event) {
            // Ensure the hidden API key input is updated before submission
            if (apiKeyInput && apiKeyHiddenInput) {
                apiKeyHiddenInput.value = apiKeyInput.value;
            }

            const scanButton = document.getElementById('scan-btn');
            if (scanButton) {
                scanButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Scanning...';
                scanButton.disabled = true;
            }
        });
    }

    // Initialize tooltips (keep existing logic)
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });

    // Handle range inputs (keep existing logic)
    const rangeInputs = document.querySelectorAll('input[type="range"]');
    rangeInputs.forEach(function(input) {
        const output = document.getElementById(input.id + '-value');
        if (output) {
            output.textContent = input.value;
            input.addEventListener('input', function() {
                output.textContent = input.value;
            });
        }
    });

    // Toggle advanced options (keep existing logic)
    const advancedToggle = document.getElementById('advanced-toggle');
    if (advancedToggle) {
        const advancedOptions = document.getElementById('advanced-options');
        advancedToggle.addEventListener('click', function() {
            if (advancedOptions) {
                advancedOptions.classList.toggle('d-none');
                const isVisible = !advancedOptions.classList.contains('d-none');
                advancedToggle.innerHTML = isVisible ? 
                    '<i data-feather="chevron-up"></i> Hide Advanced Options' : 
                    '<i data-feather="chevron-down"></i> Show Advanced Options';
                feather.replace();
            }
        });
    }

    // Form validation (keep existing logic)
    const validateInput = function(input) {
        const value = parseFloat(input.value);
        const min = parseFloat(input.min || 0);
        const max = parseFloat(input.max || Infinity);

        if (isNaN(value)) {
            input.setCustomValidity("Please enter a number");
        } else if (value < min) {
            input.setCustomValidity(`Value must be at least ${min}`);
        } else if (value > max) {
            input.setCustomValidity(`Value must be at most ${max}`);
        } else {
            input.setCustomValidity("");
        }
    };

    const numericInputs = document.querySelectorAll('input[type="number"]');
    numericInputs.forEach(function(input) {
        input.addEventListener('input', function() {
            validateInput(input);
        });

        // Initial validation
        validateInput(input);
    });

    // Update infra range labels (keep existing logic)
    const minInfra = document.getElementById('min_infra');
    const maxInfra = document.getElementById('max_infra');

    if (minInfra && maxInfra) {
        minInfra.addEventListener('change', function() {
            if (parseInt(minInfra.value) > parseInt(maxInfra.value)) {
                maxInfra.value = minInfra.value;
            }
        });

        maxInfra.addEventListener('change', function() {
            if (parseInt(maxInfra.value) < parseInt(minInfra.value)) {
                minInfra.value = maxInfra.value;
            }
        });
    }
});
