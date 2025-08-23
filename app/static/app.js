/**
 * BOM2Pic Frontend - Clean JavaScript
 * Handles authentication, file processing, and payments
 */

document.addEventListener('DOMContentLoaded', function() {
    // DOM elements
    const signupSection = document.getElementById('signupSection');
    const processingSection = document.getElementById('processingSection');
    const paymentSection = document.getElementById('paymentSection');
    const alertContainer = document.getElementById('alertContainer');
    
    // Auth elements
    const signupForm = document.getElementById('signupForm');
    const signupEmail = document.getElementById('signupEmail');
    const signupBtn = document.getElementById('signupBtn');
    const userInfo = document.getElementById('userInfo');
    const userStatus = document.getElementById('userStatus');
    const signOutBtn = document.getElementById('signOutBtn');
    const pricingInfo = document.getElementById('pricingInfo');
    
    // Processing elements
    const processingForm = document.getElementById('processingForm');
    const fileInput = document.getElementById('fileInput');
    const folderBtn = document.getElementById('folderBtn');
    const imageColumn = document.getElementById('imageColumn');
    const nameColumn = document.getElementById('nameColumn');
    const processBtn = document.getElementById('processBtn');
    
    // Payment elements
    const subscribeBtn = document.getElementById('subscribeBtn');
    const payPerFileBtn = document.getElementById('payPerFileBtn');
    
    // State
    let currentUser = null;
    let authToken = localStorage.getItem('bom2pic_token');
    let processing = false;
    
    // Initialize
    populateColumns();
    checkAuthStatus();
    handleAuthCallback();
    
    // Event Listeners
    signupForm.addEventListener('submit', handleSignup);
    signOutBtn.addEventListener('click', handleSignOut);
    processingForm.addEventListener('submit', handleProcessing);
    fileInput.addEventListener('change', handleFileSelection);
    folderBtn.addEventListener('click', handleFolderSelection);
    imageColumn.addEventListener('change', updateProcessButton);
    nameColumn.addEventListener('change', updateProcessButton);
    subscribeBtn.addEventListener('click', () => handlePayment('monthly'));
    payPerFileBtn.addEventListener('click', () => handlePayment('per_file'));
    
    // Functions
    async function handleSignup(e) {
        e.preventDefault();
        
        const email = signupEmail.value.trim();
        if (!email) {
            showAlert('danger', 'Please enter your email address.');
            return;
        }
        
        try {
            signupBtn.disabled = true;
            signupBtn.textContent = 'Sending...';
            
            const formData = new FormData();
            formData.append('email', email);
            
            const response = await fetch('/api/auth/signup', {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (response.ok) {
                showAlert('success', '📧 ' + result.message);
                signupEmail.value = '';
            } else {
                showAlert('danger', result.detail || 'Failed to send magic link');
            }
            
        } catch (error) {
            console.error('Signup error:', error);
            showAlert('danger', 'Network error. Please try again.');
        } finally {
            signupBtn.disabled = false;
            signupBtn.textContent = 'Start Free Trial';
        }
    }
    
    function handleSignOut() {
        localStorage.removeItem('bom2pic_token');
        localStorage.removeItem('bom2pic_user');
        currentUser = null;
        authToken = null;
        updateUI();
        showAlert('info', 'You have been signed out.');
    }
    
    async function handleProcessing(e) {
        e.preventDefault();
        
        if (processing) return;
        
        const files = fileInput.files;
        const imgCol = imageColumn.value;
        const nameCol = nameColumn.value;
        
        if (!files.length || !imgCol || !nameCol) {
            showAlert('danger', 'Please select files and both columns.');
            return;
        }
        
        if (imgCol === nameCol) {
            showAlert('danger', 'Image and name columns must be different.');
            return;
        }
        
        try {
            processing = true;
            updateProcessButton();
            showAlert('info', '⏳ Processing files... This may take a moment.');
            
            const formData = new FormData();
            for (let file of files) {
                formData.append('files', file);
            }
            formData.append('imageColumn', imgCol);
            formData.append('nameColumn', nameCol);
            
            const headers = {};
            if (authToken) {
                headers['Authorization'] = `Bearer ${authToken}`;
            }
            
            const response = await fetch('/process', {
                method: 'POST',
                body: formData,
                headers: headers
            });
            
            if (!response.ok) {
                if (response.status === 401) {
                    showAlert('warning', '🔐 Please sign in to process files.');
                    handleSignOut();
                    return;
                } else if (response.status === 402) {
                    const errorData = await response.json();
                    showAlert('warning', '⏰ ' + errorData.message);
                    showPaymentOptions();
                    return;
                }
                
                const errorText = await response.text();
                throw new Error(errorText);
            }
            
            // Get processing stats from headers
            const processed = response.headers.get('X-B2P-Processed') || '0';
            const saved = response.headers.get('X-B2P-Saved') || '0';
            const duplicates = response.headers.get('X-B2P-Duplicate') || '0';
            const plan = response.headers.get('X-B2P-Plan') || 'unknown';
            
            // Download the file
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            
            // Get filename from Content-Disposition header
            const contentDisposition = response.headers.get('Content-Disposition');
            const filename = contentDisposition 
                ? contentDisposition.match(/filename=([^;]+)/)?.[1] || 'images.zip'
                : 'images.zip';
            
            a.download = filename.replace(/"/g, '');
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
            
            // Show success message
            const message = `✅ Successfully processed ${processed} images (${saved} saved, ${duplicates} duplicates)!`;
            showAlert('success', message);
            
        } catch (error) {
            console.error('Processing error:', error);
            showAlert('danger', `Processing failed: ${error.message}`);
        } finally {
            processing = false;
            updateProcessButton();
        }
    }
    
    function handleFileSelection() {
        const files = Array.from(fileInput.files);
        const validFiles = files.filter(file => 
            file.name.toLowerCase().endsWith('.xlsx') && !file.name.startsWith('.')
        );
        
        if (validFiles.length !== files.length) {
            showAlert('warning', 'Some files were filtered out. Only .xlsx files are supported.');
        }
        
        // Update file input with valid files only
        const dt = new DataTransfer();
        validFiles.forEach(file => dt.items.add(file));
        fileInput.files = dt.files;
        
        updateProcessButton();
    }
    
    function handleFolderSelection() {
        const input = document.createElement('input');
        input.type = 'file';
        input.webkitdirectory = true;
        input.multiple = true;
        input.accept = '.xlsx';
        
        input.onchange = function() {
            const files = Array.from(this.files);
            const validFiles = files.filter(file => 
                file.name.toLowerCase().endsWith('.xlsx') && !file.name.startsWith('.')
            );
            
            if (validFiles.length === 0) {
                showAlert('warning', 'No valid .xlsx files found in the selected folder.');
                return;
            }
            
            const dt = new DataTransfer();
            validFiles.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
            
            showAlert('success', `Selected ${validFiles.length} .xlsx files from folder.`);
            updateProcessButton();
        };
        
        input.click();
    }
    
    async function handlePayment(plan) {
        if (!authToken) {
            showAlert('danger', 'Please sign in first.');
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('plan', plan);
            
            const response = await fetch('/api/payment/create-session', {
                method: 'POST',
                body: formData,
                headers: {
                    'Authorization': `Bearer ${authToken}`
                }
            });
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.detail || 'Payment failed');
            }
            
            const result = await response.json();
            
            // Redirect to PayPal
            window.location.href = result.checkout_url;
            
        } catch (error) {
            console.error('Payment error:', error);
            showAlert('danger', `Payment failed: ${error.message}`);
        }
    }
    
    function checkAuthStatus() {
        if (authToken) {
            // Check if we have user data too
            const userData = localStorage.getItem('bom2pic_user');
            if (userData) {
                try {
                    currentUser = JSON.parse(userData);
                    currentUser.authenticated = true;
                } catch (e) {
                    currentUser = { authenticated: true };
                }
            } else {
                currentUser = { authenticated: true };
            }
        }
        updateUI();
    }
    
    function handleAuthCallback() {
        // This function is now handled by the server callback page
        // The server stores the token and user data in localStorage
        // and redirects back to the main page
        
        // Check if we just got redirected from auth callback
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('auth') === 'success') {
            showAlert('success', '🎉 Welcome! Your 30-day free trial has started.');
            // Clean URL
            window.history.replaceState({}, document.title, window.location.pathname);
        }
    }
    
    function updateUI() {
        if (currentUser && authToken) {
            // User is authenticated - show processing interface
            signupSection.classList.add('d-none');
            processingSection.classList.remove('d-none');
            paymentSection.classList.add('d-none');
            userInfo.classList.remove('d-none');
            pricingInfo.classList.add('d-none');
            
            userStatus.textContent = 'Free Trial Active';
        } else {
            // User not authenticated - show signup
            signupSection.classList.remove('d-none');
            processingSection.classList.add('d-none');
            paymentSection.classList.add('d-none');
            userInfo.classList.add('d-none');
            pricingInfo.classList.remove('d-none');
        }
        
        updateProcessButton();
    }
    
    function showPaymentOptions() {
        processingSection.classList.add('d-none');
        paymentSection.classList.remove('d-none');
    }
    
    function updateProcessButton() {
        const hasFiles = fileInput.files.length > 0;
        const hasColumns = imageColumn.value && nameColumn.value;
        const isValid = hasFiles && hasColumns && !processing && currentUser;
        
        processBtn.disabled = !isValid;
        processBtn.textContent = processing ? 'Processing...' : '🚀 Process Files';
    }
    
    function populateColumns() {
        const columns = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');
        const defaultOption = '<option value="">Select column...</option>';
        
        imageColumn.innerHTML = defaultOption + columns.map(col => 
            `<option value="${col}">${col}</option>`
        ).join('');
        
        nameColumn.innerHTML = defaultOption + columns.map(col => 
            `<option value="${col}">${col}</option>`
        ).join('');
    }
    
    function showAlert(type, message) {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        alertContainer.innerHTML = alertHtml;
        
        // Auto-dismiss success messages after 5 seconds
        if (type === 'success') {
            setTimeout(() => {
                const alert = alertContainer.querySelector('.alert');
                if (alert) {
                    const bsAlert = new bootstrap.Alert(alert);
                    bsAlert.close();
                }
            }, 5000);
        }
    }
});
