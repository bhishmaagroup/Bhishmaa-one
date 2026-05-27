let cart = [];

document.addEventListener('DOMContentLoaded', () => {
    setupCatalog();
    setupCartControls();
    setupCheckoutForm();
});

function setupCatalog() {
    // Search products
    const searchInput = document.getElementById('catalogSearch');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value.toLowerCase().trim();
            const cards = document.querySelectorAll('.product-card-item');
            cards.forEach(card => {
                const searchText = card.getAttribute('data-search') || '';
                if (searchText.includes(query)) {
                    card.classList.remove('d-none');
                } else {
                    card.classList.add('d-none');
                }
            });
        });
    }

    // Category filter tabs
    const categoryButtons = document.querySelectorAll('#categoryFilters button');
    categoryButtons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            categoryButtons.forEach(b => b.classList.remove('btn-indigo'));
            categoryButtons.forEach(b => b.classList.add('btn-light'));
            btn.classList.remove('btn-light');
            btn.classList.add('btn-indigo');

            const categoryId = btn.getAttribute('data-category-id');
            const cards = document.querySelectorAll('.product-card-item');
            cards.forEach(card => {
                const cardCat = card.getAttribute('data-category');
                if (categoryId === 'all' || cardCat === categoryId) {
                    card.classList.remove('d-none');
                } else {
                    card.classList.add('d-none');
                }
            });
        });
    });

    // Add to cart click
    const productCards = document.querySelectorAll('.product-click-add');
    productCards.forEach(card => {
        card.addEventListener('click', () => {
            const id = card.getAttribute('data-id');
            const name = card.getAttribute('data-name');
            const price = parseFloat(card.getAttribute('data-price') || '0.00');
            const gst = parseFloat(card.getAttribute('data-gst') || '18.00');
            const stock = parseFloat(card.getAttribute('data-stock') || '0.00');
            
            addToCart(id, name, price, gst, stock);
        });
    });
}

function addToCart(id, name, price, gst, stock) {
    const existing = cart.find(item => item.id === id);
    if (existing) {
        if (existing.quantity >= stock) {
            alert(`Insufficient stock. Only ${stock} units available at this branch.`);
            return;
        }
        existing.quantity += 1;
    } else {
        if (stock <= 0) {
            alert(`Insufficient stock. Available: 0 units.`);
            return;
        }
        cart.push({
            id: id,
            name: name,
            price: price,
            gst: gst,
            quantity: 1,
            stock: stock
        });
    }
    renderCart();
}

function setupCartControls() {
    const clearBtn = document.getElementById('btnClearCart');
    if (clearBtn) {
        clearBtn.addEventListener('click', () => {
            cart = [];
            renderCart();
        });
    }

    const discountInput = document.getElementById('discount');
    if (discountInput) {
        discountInput.addEventListener('input', () => {
            calculateTotals();
        });
    }
}

function renderCart() {
    const cartList = document.getElementById('cartItemsList');
    const emptyRow = document.getElementById('emptyCartRow');

    if (!cartList) return;

    // Clear previous dynamic items
    const rows = cartList.querySelectorAll('.cart-row-item');
    rows.forEach(r => r.remove());

    if (cart.length === 0) {
        if (emptyRow) emptyRow.classList.remove('d-none');
        calculateTotals();
        return;
    }

    if (emptyRow) emptyRow.classList.add('d-none');

    cart.forEach((item, index) => {
        const row = document.createElement('tr');
        row.className = 'cart-row-item';
        
        const subtotal = item.price * item.quantity;
        const tax = subtotal * (item.gst / 100);
        const total = subtotal + tax;

        row.innerHTML = `
            <td>
                <div class="fw-bold text-main text-truncate" style="max-width: 150px;">${item.name}</div>
                <span class="text-muted small">₹${item.price.toFixed(2)} + ${item.gst}% GST</span>
            </td>
            <td>
                <div class="input-group input-group-sm" style="width: 85px;">
                    <button class="btn btn-outline-secondary btn-qty-minus" type="button" data-index="${index}">-</button>
                    <input type="text" class="form-control text-center p-0 input-qty" value="${item.quantity}" data-index="${index}" readonly>
                    <button class="btn btn-outline-secondary btn-qty-plus" type="button" data-index="${index}">+</button>
                </div>
            </td>
            <td class="fw-bold text-main">₹${total.toFixed(2)}</td>
            <td class="text-end">
                <button type="button" class="btn btn-sm btn-icon btn-light rounded-circle text-danger btn-remove-item" data-index="${index}">
                    <i class="bi bi-x-lg"></i>
                </button>
            </td>
        `;
        cartList.appendChild(row);
    });

    // Add listeners to new controls
    cartList.querySelectorAll('.btn-qty-minus').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(btn.getAttribute('data-index'));
            if (cart[idx].quantity > 1) {
                cart[idx].quantity -= 1;
                renderCart();
            }
        });
    });

    cartList.querySelectorAll('.btn-qty-plus').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const idx = parseInt(btn.getAttribute('data-index'));
            if (cart[idx].quantity < cart[idx].stock) {
                cart[idx].quantity += 1;
                renderCart();
            } else {
                alert(`Insufficient stock. Only ${cart[idx].stock} units available.`);
            }
        });
    });

    cartList.querySelectorAll('.btn-remove-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const idx = parseInt(btn.getAttribute('data-index'));
            cart.splice(idx, 1);
            renderCart();
        });
    });

    calculateTotals();
}

function calculateTotals() {
    let subtotalSum = 0;
    let taxSum = 0;

    cart.forEach(item => {
        const itemSubtotal = item.price * item.quantity;
        const itemTax = itemSubtotal * (item.gst / 100);
        subtotalSum += itemSubtotal;
        taxSum += itemTax;
    });

    const discountInput = document.getElementById('discount');
    const discountVal = discountInput ? parseFloat(discountInput.value || '0.00') : 0.00;

    const grandTotal = Math.max(0, (subtotalSum + taxSum) - discountVal);

    // Update UI elements
    document.getElementById('summarySubtotal').innerText = `₹ ${subtotalSum.toFixed(2)}`;
    document.getElementById('summaryGST').innerText = `₹ ${taxSum.toFixed(2)}`;
    document.getElementById('summaryDiscount').innerText = `- ₹ ${discountVal.toFixed(2)}`;
    document.getElementById('summaryTotal').innerText = `₹ ${grandTotal.toFixed(2)}`;
}

function setupCheckoutForm() {
    const form = document.getElementById('checkoutForm');
    if (!form) return;

    form.addEventListener('submit', (e) => {
        e.preventDefault();

        if (cart.length === 0) {
            alert('Cannot checkout with an empty cart.');
            return;
        }

        const name = document.getElementById('customer_name').value || 'Walk-in Client';
        const phone = document.getElementById('customer_phone').value || '';
        const mode = document.getElementById('payment_mode').value || 'Cash';
        const discountInput = document.getElementById('discount');
        const discountVal = discountInput ? parseFloat(discountInput.value || '0.00') : 0.00;

        const payload = {
            customer_name: name,
            customer_phone: phone,
            payment_mode: mode,
            discount: discountVal,
            status: 'Paid',  // POS sales are completed directly
            items: cart.map(item => ({
                product_name: item.name,
                quantity: item.quantity,
                unit_price: item.price,
                gst_rate: item.gst
            }))
        };

        // CSRF Token header
        const csrfTokenElement = document.querySelector('input[name="csrf_token"]');
        const csrfToken = csrfTokenElement ? csrfTokenElement.value : '';

        fetch(POST_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify(payload)
        })
        .then(response => {
            if (!response.ok) {
                return response.text().then(text => {
                    let errMsg = 'Checkout failed';
                    try {
                        const parsed = JSON.parse(text);
                        errMsg = parsed.error || errMsg;
                    } catch (e) {
                        errMsg = `Server error (${response.status})`;
                    }
                    throw new Error(errMsg);
                });
            }
            return response.json();
        })
        .then(res => {
            alert('Transaction completed successfully!');
            // Print receipt in new window
            window.open(`/billing/print/${res.id}`, '_blank');
            // Reset state
            cart = [];
            document.getElementById('customer_name').value = 'Walk-in Client';
            document.getElementById('customer_phone').value = '';
            if (discountInput) discountInput.value = '0.00';
            renderCart();
        })
        .catch(err => {
            alert(`Checkout Error: ${err.message}`);
        });
    });
}
