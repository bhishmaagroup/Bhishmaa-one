document.addEventListener("DOMContentLoaded", function() {
    const userIdSelect = document.getElementById("userIdSelect");
    const monthSelect = document.getElementById("monthSelect");
    const yearSelect = document.getElementById("yearSelect");
    const allowancesInput = document.getElementById("allowancesInput");
    const deductionsInput = document.getElementById("deductionsInput");
    
    // Preview containers
    const spinner = document.getElementById("previewSpinner");
    const emptyState = document.getElementById("previewEmptyState");
    const content = document.getElementById("previewContent");
    
    // Preview values
    const presentNode = document.getElementById("previewPresent");
    const absentNode = document.getElementById("previewAbsent");
    const leaveNode = document.getElementById("previewLeave");
    const lateNode = document.getElementById("previewLate");
    const basicNode = document.getElementById("previewBasic");
    const additionsNode = document.getElementById("previewAdditions");
    const lopNode = document.getElementById("previewLopDeductions");
    const manualDeductNode = document.getElementById("previewManualDeductions");
    const netNode = document.getElementById("previewNetPay");
    
    // Hold calculated base figures
    let cachedBasic = 0.0;
    let cachedLopDeductions = 0.0;
    
    function loadPreview() {
        const userId = userIdSelect.value;
        const month = monthSelect.value;
        const year = yearSelect.value;
        
        if (!userId || !month || !year) {
            emptyState.classList.remove("d-none");
            content.classList.add("d-none");
            spinner.classList.add("d-none");
            return;
        }
        
        // Show spinner
        spinner.classList.remove("d-none");
        emptyState.classList.add("d-none");
        content.classList.add("d-none");
        
        fetch(`${PREVIEW_API_URL}?user_id=${encodeURIComponent(userId)}&month=${encodeURIComponent(month)}&year=${encodeURIComponent(year)}`)
            .then(res => res.json())
            .then(data => {
                spinner.classList.add("d-none");
                if (data.error) {
                    emptyState.classList.remove("d-none");
                    return;
                }
                
                content.classList.remove("d-none");
                
                // Set indicators
                presentNode.innerText = data.present_days.toFixed(1);
                absentNode.innerText = data.absent_days.toFixed(1);
                leaveNode.innerText = data.leave_days.toFixed(1);
                lateNode.innerText = data.late_days;
                
                cachedBasic = data.basic_salary;
                cachedLopDeductions = data.suggested_deductions;
                
                // Prefill form deductions with LOP suggestion if empty or default
                if (deductionsInput.value === "0.0" || deductionsInput.value === "" || parseFloat(deductionsInput.value) === 0.0) {
                    deductionsInput.value = cachedLopDeductions.toFixed(2);
                }
                
                basicNode.innerText = `₹ ${cachedBasic.toFixed(2)}`;
                lopNode.innerText = `₹ ${cachedLopDeductions.toFixed(2)}`;
                
                recalculateNetPay();
            })
            .catch(err => {
                spinner.classList.add("d-none");
                emptyState.classList.remove("d-none");
                console.error("Preview load failed:", err);
            });
    }
    
    function recalculateNetPay() {
        const additions = parseFloat(allowancesInput.value) || 0.0;
        const manualDeductionsInput = parseFloat(deductionsInput.value) || 0.0;
        
        // Manual deduction over LOP calculation
        const addedManualDeductions = Math.max(0.0, manualDeductionsInput - cachedLopDeductions);
        
        additionsNode.innerText = `₹ ${additions.toFixed(2)}`;
        manualDeductNode.innerText = `₹ ${addedManualDeductions.toFixed(2)}`;
        
        const netPay = Math.max(0.0, cachedBasic + additions - manualDeductionsInput);
        netNode.innerText = `₹ ${netPay.toFixed(2)}`;
    }
    
    // Bind listeners
    userIdSelect.addEventListener("change", loadPreview);
    monthSelect.addEventListener("change", loadPreview);
    yearSelect.addEventListener("change", loadPreview);
    
    allowancesInput.addEventListener("input", recalculateNetPay);
    deductionsInput.addEventListener("input", recalculateNetPay);
    
    // Initial load
    loadPreview();
});
