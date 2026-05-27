// Billing POS Client Engine
document.addEventListener("DOMContentLoaded", function() {
    let cart = [];
    
    const btnAddItem = document.getElementById("btnAddItem");
    const cartItemsList = document.getElementById("cartItemsList");
    const emptyCartRow = document.getElementById("emptyCartRow");
    
    // Summary DOM nodes
    const summarySubtotal = document.getElementById("summarySubtotal");
    const summaryCGST = document.getElementById("summaryCGST");
    const summarySGST = document.getElementById("summarySGST");
    const summaryIGST = document.getElementById("summaryIGST");
    const summaryDiscount = document.getElementById("summaryDiscount");
    const summaryTotal = document.getElementById("summaryTotal");
    
    const cgstRow = document.getElementById("cgstRow");
    const sgstRow = document.getElementById("sgstRow");
    const igstRow = document.getElementById("igstRow");
    
    // Summary DOM nodes for payment tracking
    const summaryPaid = document.getElementById("summaryPaid");
    const summaryDue = document.getElementById("summaryDue");
    
    // Forms
    const checkoutForm = document.getElementById("checkoutForm");
    const customerStateSelect = document.getElementById("customer_state_code");
    const discountInput = document.getElementById("discount");
    const statusSelect = document.getElementById("status");
    const amountPaidInput = document.getElementById("amount_paid");
    
    // Event listeners
    btnAddItem.addEventListener("click", addItem);
    customerStateSelect.addEventListener("change", recalculateTotals);
    discountInput.addEventListener("input", recalculateTotals);
    statusSelect.addEventListener("change", function() {
        toggleAmountPaidField();
        recalculateTotals();
    });
    amountPaidInput.addEventListener("input", recalculateTotals);
    checkoutForm.addEventListener("submit", processCheckout);

    // Initialize payment field state
    toggleAmountPaidField();
    recalculateTotals();
    
    // Autocomplete for products
    const itemNameInput = document.getElementById("itemName");
    const itemPriceInput = document.getElementById("itemPrice");
    const itemGstSelect = document.getElementById("itemGst");
    const itemSuggestions = document.getElementById("itemSuggestions");
    
    itemNameInput.addEventListener("input", function() {
        const query = this.value.trim();
        if (query.length < 2) {
            itemSuggestions.innerHTML = "";
            itemSuggestions.classList.add("d-none");
            return;
        }
        
        fetch(`/inventory/api/products?q=${encodeURIComponent(query)}`)
            .then(res => res.json())
            .then(data => {
                itemSuggestions.innerHTML = "";
                if (data.products && data.products.length > 0) {
                    itemSuggestions.classList.remove("d-none");
                    data.products.forEach(prod => {
                        const btn = document.createElement("button");
                        btn.type = "button";
                        btn.className = "list-group-item list-group-item-action small d-flex justify-content-between align-items-center";
                        btn.innerHTML = `
                            <span><strong>${prod.name}</strong> <span class="text-muted font-monospace small">#${prod.sku}</span></span>
                            <span class="badge bg-indigo-light text-indigo">₹ ${prod.selling_price.toFixed(2)}</span>
                        `;
                        btn.addEventListener("click", function() {
                            itemNameInput.value = prod.name;
                            itemPriceInput.value = prod.selling_price.toFixed(2);
                            
                            // Select matching GST choice
                            const matchedGst = Math.round(prod.gst_rate).toString();
                            for (let i = 0; i < itemGstSelect.options.length; i++) {
                                const optVal = parseFloat(itemGstSelect.options[i].value);
                                if (Math.round(optVal).toString() === matchedGst) {
                                    itemGstSelect.selectedIndex = i;
                                    break;
                                }
                            }
                            
                            itemSuggestions.innerHTML = "";
                            itemSuggestions.classList.add("d-none");
                        });
                        itemSuggestions.appendChild(btn);
                    });
                } else {
                    itemSuggestions.classList.add("d-none");
                }
            })
            .catch(err => {
                console.error("Failed to query products:", err);
            });
    });
    
    // Autocomplete for customers
    const customerNameInput = document.getElementById("customer_name");
    const customerPhoneInput = document.getElementById("customer_phone");
    const customerGstinInput = document.getElementById("customer_gstin");
    const customerSuggestions = document.getElementById("customerSuggestions");
    
    function showCustomerSuggestions(inputElement) {
        inputElement.addEventListener("input", function() {
            const query = this.value.trim();
            if (query.length < 2) {
                customerSuggestions.innerHTML = "";
                customerSuggestions.classList.add("d-none");
                return;
            }
            
            fetch(`/crm/api/customers?q=${encodeURIComponent(query)}`)
                .then(res => res.json())
                .then(data => {
                    customerSuggestions.innerHTML = "";
                    if (data.customers && data.customers.length > 0) {
                        customerSuggestions.classList.remove("d-none");
                        data.customers.forEach(cust => {
                            const btn = document.createElement("button");
                            btn.type = "button";
                            btn.className = "list-group-item list-group-item-action small d-flex justify-content-between align-items-center";
                            
                            // Create text showing name, phone, and optional GSTIN/Balance
                            let detailsText = "";
                            if (cust.phone) detailsText += ` (${cust.phone})`;
                            if (cust.outstanding_balance > 0) {
                                detailsText += ` | Balance: ₹${cust.outstanding_balance.toFixed(2)}`;
                            }
                            
                            btn.innerHTML = `
                                <span><strong>${cust.name}</strong><span class="text-muted small">${detailsText}</span></span>
                                ${cust.gstin ? `<span class="badge bg-success-light text-success font-monospace small">${cust.gstin}</span>` : ''}
                            `;
                            
                            btn.addEventListener("click", function() {
                                customerNameInput.value = cust.name;
                                customerPhoneInput.value = cust.phone || "";
                                customerGstinInput.value = cust.gstin || "";
                                
                                // Select matching state code
                                if (cust.state_code) {
                                    customerStateSelect.value = cust.state_code;
                                }
                                
                                customerSuggestions.innerHTML = "";
                                customerSuggestions.classList.add("d-none");
                                
                                // Trigger recalculation since state code might have changed
                                recalculateTotals();
                            });
                            customerSuggestions.appendChild(btn);
                        });
                    } else {
                        customerSuggestions.classList.add("d-none");
                    }
                })
                .catch(err => {
                    console.error("Failed to query customers:", err);
                });
        });
    }
    
    if (customerNameInput && customerSuggestions) {
        showCustomerSuggestions(customerNameInput);
    }
    if (customerPhoneInput && customerSuggestions) {
        showCustomerSuggestions(customerPhoneInput);
    }
    
    // Hide suggestions when clicking outside
    document.addEventListener("click", function(e) {
        if (e.target !== itemNameInput && e.target !== itemSuggestions) {
            itemSuggestions.innerHTML = "";
            itemSuggestions.classList.add("d-none");
        }
        if (e.target !== customerNameInput && e.target !== customerPhoneInput && e.target !== customerSuggestions) {
            customerSuggestions.innerHTML = "";
            customerSuggestions.classList.add("d-none");
        }
    });
    
    function addItem() {
        const nameInput = document.getElementById("itemName");
        const priceInput = document.getElementById("itemPrice");
        const qtyInput = document.getElementById("itemQty");
        const gstSelect = document.getElementById("itemGst");
        
        const name = nameInput.value.trim();
        const price = parseFloat(priceInput.value);
        const qty = parseFloat(qtyInput.value);
        const gst = parseFloat(gstSelect.value);
        
        if (!name) {
            alert("Please enter a valid product/item name.");
            nameInput.focus();
            return;
        }
        if (isNaN(price) || price < 0) {
            alert("Please enter a valid positive unit price.");
            priceInput.focus();
            return;
        }
        if (isNaN(qty) || qty <= 0) {
            alert("Quantity must be greater than zero.");
            qtyInput.focus();
            return;
        }
        
        // Check if item already in cart
        const existingIdx = cart.findIndex(item => item.product_name.toLowerCase() === name.toLowerCase() && item.gst_rate === gst);
        if (existingIdx !== -1) {
            cart[existingIdx].quantity += qty;
        } else {
            cart.push({
                product_name: name,
                unit_price: price,
                quantity: qty,
                gst_rate: gst
            });
        }
        
        // Reset item entry bar
        nameInput.value = "";
        priceInput.value = "";
        qtyInput.value = "1";
        gstSelect.selectedIndex = 3; // Reset to 18% default
        
        renderCart();
        nameInput.focus();
    }
    
    function deleteItem(index) {
        cart.splice(index, 1);
        renderCart();
    }
    
    function updateQty(index, newQty) {
        const qty = parseFloat(newQty);
        if (isNaN(qty) || qty <= 0) {
            deleteItem(index);
        } else {
            cart[index].quantity = qty;
            renderCart();
        }
    }
    
    function renderCart() {
        // Clear dynamic rows
        const rows = cartItemsList.querySelectorAll(".cart-row");
        rows.forEach(r => r.remove());
        
        if (cart.length === 0) {
            emptyCartRow.classList.remove("d-none");
        } else {
            emptyCartRow.classList.add("d-none");
            
            cart.forEach((item, index) => {
                const tr = document.createElement("tr");
                tr.className = "cart-row";
                
                const lineSubtotal = item.unit_price * item.quantity;
                const lineTax = lineSubtotal * (item.gst_rate / 100.0);
                const lineTotal = lineSubtotal + lineTax;
                
                tr.innerHTML = `
                    <td class="fw-semibold text-main">${item.product_name}</td>
                    <td>₹ ${item.unit_price.toFixed(2)}</td>
                    <td>
                        <input type="number" class="form-control form-control-sm text-center qty-input" 
                               value="${item.quantity}" min="0.1" step="any" 
                               style="width: 80px;" data-index="${index}">
                    </td>
                    <td>${item.gst_rate}%</td>
                    <td>₹ ${lineTax.toFixed(2)}</td>
                    <td class="fw-bold">₹ ${lineTotal.toFixed(2)}</td>
                    <td class="text-end">
                        <button type="button" class="btn btn-icon btn-danger-light rounded-circle btn-delete" data-index="${index}">
                            <i class="bi bi-trash"></i>
                        </button>
                    </td>
                `;
                
                cartItemsList.appendChild(tr);
            });
            
            // Rebind listeners
            cartItemsList.querySelectorAll(".qty-input").forEach(input => {
                input.addEventListener("change", function() {
                    updateQty(this.dataset.index, this.value);
                });
            });
            
            cartItemsList.querySelectorAll(".btn-delete").forEach(btn => {
                btn.addEventListener("click", function() {
                    deleteItem(this.dataset.index);
                });
            });
        }
        
        recalculateTotals();
    }
    
    function recalculateTotals() {
        let subtotal = 0.0;
        let cgst = 0.0;
        let sgst = 0.0;
        let igst = 0.0;
        
        const customerStateCode = customerStateSelect.value;
        const isIntrastate = (customerStateCode === ORG_STATE_CODE);
        
        cart.forEach(item => {
            const lineSubtotal = item.unit_price * item.quantity;
            const lineTax = lineSubtotal * (item.gst_rate / 100.0);
            
            subtotal += lineSubtotal;
            
            if (isIntrastate) {
                cgst += lineTax / 2.0;
                sgst += lineTax / 2.0;
            } else {
                igst += lineTax;
            }
        });
        
        const discount = parseFloat(discountInput.value) || 0.0;
        const totalTax = cgst + sgst + igst;
        const grandTotal = Math.max(0.0, subtotal + totalTax - discount);
        
        // Update views
        summarySubtotal.innerText = `₹ ${subtotal.toFixed(2)}`;
        summaryCGST.innerText = `₹ ${cgst.toFixed(2)}`;
        summarySGST.innerText = `₹ ${sgst.toFixed(2)}`;
        summaryIGST.innerText = `₹ ${igst.toFixed(2)}`;
        summaryDiscount.innerText = `- ₹ ${discount.toFixed(2)}`;
        summaryTotal.innerText = `₹ ${grandTotal.toFixed(2)}`;

        const status = statusSelect.value;
        let amountPaid = 0.0;
        if (status === 'Paid') {
            amountPaid = grandTotal;
        } else if (status === 'Partial') {
            amountPaid = parseFloat(amountPaidInput.value) || 0.0;
        }

        const pendingAmount = Math.max(0.0, grandTotal - amountPaid);
        summaryPaid.innerText = `₹ ${amountPaid.toFixed(2)}`;
        summaryDue.innerText = `₹ ${pendingAmount.toFixed(2)}`;

        // Toggle view split rows
        if (isIntrastate) {
            cgstRow.classList.remove("d-none");
            sgstRow.classList.remove("d-none");
            igstRow.classList.add("d-none");
        } else {
            cgstRow.classList.add("d-none");
            sgstRow.classList.add("d-none");
            igstRow.classList.remove("d-none");
        }
    }

    function toggleAmountPaidField() {
        if (!amountPaidInput) {
            return;
        }

        const status = statusSelect.value;
        if (status === 'Paid') {
            amountPaidInput.value = summaryTotal.innerText.replace(/[₹,\s]/g, '') || '0.00';
            amountPaidInput.disabled = true;
        } else if (status === 'Partial') {
            amountPaidInput.disabled = false;
        } else {
            amountPaidInput.value = '0.00';
            amountPaidInput.disabled = true;
        }
    }
    
    function processCheckout(e) {
        e.preventDefault();
        
        if (cart.length === 0) {
            alert("Cannot complete checkout because the POS cart is empty.");
            return;
        }
        
        // Gather data
        const customer_name = document.getElementById("customer_name").value.trim();
        const customer_phone = document.getElementById("customer_phone").value.trim();
        const customer_state_code = customerStateSelect.value;
        const customer_gstin = document.getElementById("customer_gstin").value.trim();
        const payment_mode = document.getElementById("payment_mode").value;
        const status = document.getElementById("status").value;
        const amount_paid = parseFloat(amountPaidInput.value) || 0.0;
        const discount = parseFloat(discountInput.value) || 0.0;
        
        // Clear previous error messages
        document.querySelectorAll(".error-message").forEach(el => el.innerText = "");
        
        const payload = {
            customer_name,
            customer_phone,
            customer_state_code,
            customer_gstin,
            payment_mode,
            status,
            amount_paid,
            discount,
            items: cart
        };
        
        // Submit via AJAX
        fetch(POST_URL, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": document.querySelector("input[name='csrf_token']").value
            },
            body: JSON.stringify(payload)
        })
        .then(response => response.json().then(data => ({ status: response.status, body: data })))
        .then(res => {
            if (res.status === 201) {
                // Success - redirect to invoice registry
                window.location.href = REDIRECT_URL;
            } else {
                // Display error
                if (res.body.error) {
                    alert("Error: " + res.body.error);
                } else if (res.body.errors) {
                    // wtforms style fields error map
                    for (const field in res.body.errors) {
                        const errNode = document.getElementById("err-" + field);
                        if (errNode) {
                            errNode.innerText = res.body.errors[field].join(", ");
                        }
                    }
                }
            }
        })
        .catch(err => {
            console.error("Checkout failed:", err);
            alert("Checkout transaction failed due to network / server errors.");
        });
    }
});
