
// --- App Navigation and Rendering ---

const appState = {
    view: 'home',
    query: '',
    selectedProductId: null,
    auth: {
        loggedIn: false,
        username: null
    }
};

const DOMElements = {
    main: document.getElementById('main-content'),
    modal: document.getElementById('image-upload-modal'),
    uploadArea: document.getElementById('upload-area'),
    uploadStatus: document.getElementById('upload-status'),
    fileInput: document.getElementById('file-input')
};

function init() {
    checkAuth().then(() => {
        renderNavActions();
        renderView('home');
        setupUploadListeners();
    });
}

function navigate(view, params = {}) {
    appState.view = view;
    Object.assign(appState, params);
    renderView(view);
    window.scrollTo(0, 0);
}

function renderView(view) {
    DOMElements.main.innerHTML = '';
    const template = document.getElementById(`template-${view}`);
    if (template) {
        DOMElements.main.appendChild(template.content.cloneNode(true));

        // Post-render attachments
        if (view === 'home') {
            renderTrending();
            const input = document.getElementById('search-input');
            input.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleSearch();
            });
        } else if (view === 'results') {
            document.getElementById('results-search-input').value = appState.query;
            document.getElementById('results-search-input').addEventListener('keypress', (e) => {
                if (e.key === 'Enter') handleSearch(e.target.value);
            });
            executeSearch();
        } else if (view === 'compare') {
            renderCompare();
        }
    }
}

// --- View Specific Logic ---

async function renderTrending() {
    const container = document.getElementById('trending-container');
    if (!container) return;

    try {
        const response = await fetch('/api/trending');
        const trending = await response.json();
        container.innerHTML = trending.map(p => createProductCard(p)).join('');
    } catch (error) {
        console.error("Error fetching trending products:", error);
    }
}

function handleSearch(queryOverride = null) {
    let q = queryOverride;
    if (q === null) {
        const input = document.getElementById('search-input');
        q = input ? input.value : '';
    }

    if (q && q.trim() !== '') {
        navigate('results', { query: q });
    }
}

async function executeSearch() {
    const query = appState.query;
    const resultsContainer = document.getElementById('search-results-container');
    const tagsContainer = document.getElementById('ai-query-expansion');

    // Show loading skeleton grid
    if (resultsContainer) {
        resultsContainer.innerHTML = Array(6).fill().map(() => `
            <div class="product-card skeleton" style="height: 320px; border: none; box-shadow: none;"></div>
        `).join('');
    }

    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const data = await response.json();

        // AI #1: Expand Query
        if (tagsContainer && data.insight) {
            tagsContainer.innerHTML = data.insight.expansions.map(tag => `<span class="tag" onclick="handleSearch('${tag}')">${tag}</span>`).join('');
        }

        if (resultsContainer) {
            if (data.results && data.results.length > 0) {
                resultsContainer.innerHTML = data.results.map(p => createProductCard(p)).join('');
            } else if (data.fallback) {
                // Suggest fallback item if nothing matches exactly to keep UX smooth
                resultsContainer.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 2rem;">
                        <p style="margin-bottom: 1rem; color: var(--text-secondary);">ไม่พบสินค้าที่ตรงกับ "${query}" ขอแนะนำสินค้ายอดนิยมแทน:</p>
                    </div>
                    ${createProductCard(data.fallback)}
                `;
            } else {
                resultsContainer.innerHTML = `
                    <div style="grid-column: 1/-1; text-align: center; padding: 2rem;">
                        <p style="margin-bottom: 1rem; color: var(--text-secondary);">ไม่พบสินค้า</p>
                    </div>
                 `;
            }
        }
    } catch (error) {
        console.error("Search error:", error);
    }
}

function createProductCard(product) {
    if (!product || !product.listings || product.listings.length === 0) return '';
    const sortedListings = [...product.listings].sort((a, b) => a.price - b.price);
    const topListing = sortedListings[0];
    const officialListing = sortedListings.find(l => l.is_official);
    const lowestPrice = topListing.price;
    const avgRating = (product.listings.reduce((acc, l) => acc + l.rating, 0) / product.listings.length).toFixed(1);

    const otherCount = sortedListings.length - 1;

    // logic for badges
    let badges = '';
    // If official store has the same price as the lowest, it's the absolute best deal
    if (officialListing && officialListing.price === lowestPrice) {
        badges += `<div class="p-badge p-badge-best"><i class="fa-solid fa-crown"></i> ดีลที่ดีที่สุด (ร้านทางการ)</div>`;
    } else {
        // Otherwise show separately
        badges += `<div class="p-badge p-badge-price"><i class="fa-solid fa-tags"></i> ถูกที่สุด ฿${lowestPrice.toLocaleString()}</div>`;
        if (officialListing) {
            badges += `<div class="p-badge p-badge-official"><i class="fa-solid fa-circle-check"></i> มีร้านทางการ</div>`;
        }
    }

    return `
        <div class="product-card" onclick="navigate('compare', '${product.id}')" style="animation: fadeUp 0.4s ease backwards;">
            <div class="image-container" style="position: relative;">
                <a href="${topListing.link}" target="_blank" onclick="event.stopPropagation();" title="ไปที่ร้านค้า">
                    <img src="${product.image}" alt="${product.name}" class="product-img" loading="lazy" onerror="this.src='https://via.placeholder.com/300?text=No+Image';">
                </a>
                <div class="rating-badge" style="position: absolute; top: 10px; right: 10px; background: rgba(0,0,0,0.6); color: white; padding: 2px 6px; border-radius: 4px; font-size: 0.8rem; pointer-events: none;">
                    <i class="fa-solid fa-star" style="color: #FFD700;"></i> ${avgRating}
                </div>
                <div class="card-badges-container">
                    ${badges}
                </div>
            </div>
            <div class="product-info" style="padding: 1rem;">
                <h3 style="font-size: 0.95rem; margin-bottom: 0.5rem; line-height: 1.4; height: 2.8rem; overflow: hidden; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;">${product.name}</h3>
                
                <div style="font-size: 0.85rem; color: var(--text-secondary); margin-bottom: 0.5rem; display: flex; align-items: center; gap: 0.5rem;">
                   <i class="fa-solid fa-store" style="color: var(--accent-blue);"></i> 
                   <span>${topListing.platform} ${topListing.is_official ? '<i class="fa-solid fa-circle-check" style="color: var(--blue-500); font-size: 0.7rem;"></i>' : ''}</span>
                </div>
                
                <div class="price-container" style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 1rem;">
                    <div>
                        <span style="font-size: 0.8rem; color: var(--text-secondary);">เริ่มต้น</span>
                        <div class="price" style="font-size: 1.3rem; font-weight: 700; color: var(--green-600);">฿${lowestPrice.toLocaleString()}</div>
                    </div>
                    ${otherCount > 0 ? `<div style="font-size: 0.75rem; background: #ebf8ff; color: #2b6cb0; padding: 4px 8px; border-radius: 20px; font-weight: 600;">เปรียบเทียบ ${otherCount + 1} ร้าน</div>` : ''}
                </div>
                
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem;">
                    <button class="btn-outline" style="padding: 0.5rem; font-size: 0.85rem;" onclick="event.stopPropagation(); navigate('compare', '${product.id}')">
                        <i class="fa-solid fa-scale-balanced"></i> เช็คราคา
                    </button>
                    <a href="${topListing.link}" target="_blank" class="btn-primary" style="text-decoration: none; padding: 0.5rem; font-size: 0.85rem; text-align: center; border-radius: 8px; font-weight: 600;" onclick="event.stopPropagation();">
                        <i class="fa-solid fa-cart-shopping"></i> ซื้อเลย
                    </a>
                </div>
            </div>
        </div>
    `;
}

async function renderCompare() {
    const headerContainer = document.getElementById('compare-product-header');
    const aiPanel = document.getElementById('ai-recommendation-panel');
    const tableBody = document.getElementById('comparison-table-body');

    try {
        const response = await fetch(`/api/product/${appState.selectedProductId}`);
        if (!response.ok) {
            navigate('home');
            return;
        }

        const data = await response.json();
        const product = data.product;
        const aiDeal = data.recommendation;

        // Header Info
        headerContainer.innerHTML = `
            <img src="${product.image}" alt="${product.name}">
            <div class="compare-product-info">
                <h2>${product.name}</h2>
                <p style="color: var(--text-secondary)"><i class="fa-solid fa-tag"></i> พบสินค้าจาก ${product.listings.length} แพลตฟอร์ม</p>
            </div>
        `;

        // AI #2 Recommendation
        aiPanel.innerHTML = `
            <div class="ai-header">
                <i class="fa-solid fa-bolt"></i> คำแนะนำจาก AI: ดีลที่ดีที่สุด
            </div>
            <div style="margin-top: 0.5rem; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 1rem;">
                <div>
                    <strong>${aiDeal.platform}</strong>
                    <p style="margin-top: 4px; font-size: 0.9rem;">เหตุผล: ${aiDeal.reason}</p>
                </div>
                <a href="${aiDeal.link}" target="_blank" class="btn-primary" style="text-decoration: none;">ไปยังร้านค้า</a>
            </div>
        `;

        // Table
        // Sort listings by price low to high for better UX
        const sortedListings = [...product.listings].sort((a, b) => a.price - b.price);

        tableBody.innerHTML = sortedListings.map(listing => {
            const isBestDeal = listing.platform === aiDeal.platform;

            let platformIcon = 'fa-store';
            let platformColor = 'var(--text-secondary)';
            if (listing.platform.includes('Shopee')) { platformColor = '#EE4D2D'; platformIcon = 'fa-bag-shopping'; }
            if (listing.platform.includes('Lazada')) { platformColor = '#0F146D'; platformIcon = 'fa-heart'; }
            if (listing.platform.includes('Amazon')) { platformColor = '#FF9900'; platformIcon = 'fa-amazon'; }

            return `
                <tr style="${isBestDeal ? 'background-color: rgba(56, 161, 105, 0.05);' : ''}">
                    <td>
                        <div class="platform-name" style="margin-bottom: 4px;">
                            <i class="fa-solid ${platformIcon}" style="color: ${platformColor}"></i> 
                            ${listing.platform} ${listing.is_official ? '<span class="tag" style="background:var(--blue-500); padding: 0 4px; font-size: 0.65rem;"><i class="fa-solid fa-check-circle"></i> Official</span>' : ''}
                            ${isBestDeal ? '<span class="tag" style="background:var(--green-500); padding: 0 4px; font-size: 0.65rem;">แนะนำ</span>' : ''}
                        </div>
                        <div style="font-size: 0.8rem; color: var(--text-secondary); line-height: 1.2; word-break: break-word; max-width: 250px;">
                            ${listing.title || ''}
                        </div>
                    </td>
                    <td style="font-weight: 700; color: var(--text-primary); vertical-align: middle;">฿${listing.price.toLocaleString()}</td>
                    <td style="vertical-align: middle;"><span class="rating"><i class="fa-solid fa-star"></i> ${listing.rating ? listing.rating.toFixed(1) : '-'}</span></td>
                    <td style="vertical-align: middle;">
                        <a href="${listing.link}" target="_blank" class="${isBestDeal ? 'btn-secondary' : 'btn-primary'}" style="text-decoration: none; padding: 0.4rem 0.8rem; font-size: 0.9rem; white-space: nowrap;">
                            ซื้อสินค้า
                        </a>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (error) {
        console.error("Error fetching product details:", error);
    }
}

// --- Image Upload Flow Validation ---

function openImageUpload() {
    DOMElements.modal.classList.remove('hidden');
    DOMElements.uploadArea.classList.remove('hidden');
    DOMElements.uploadStatus.classList.add('hidden');

    // Check if image-selection-area is available and hide it
    const selectArea = document.getElementById('image-selection-area');
    if (selectArea) {
        selectArea.classList.add('hidden');
    }
}

function closeImageUpload() {
    DOMElements.modal.classList.add('hidden');
    DOMElements.fileInput.value = '';
    const bb = document.getElementById('bounding-boxes');
    if (bb) bb.innerHTML = '';
}

function setupUploadListeners() {
    DOMElements.uploadArea.addEventListener('click', () => {
        DOMElements.fileInput.click();
    });

    DOMElements.fileInput.addEventListener('change', (e) => {
        if (e.target.files && e.target.files.length > 0) {
            simulateImageUpload(e.target.files[0]);
        }
    });

    // Drag and drop setup
    DOMElements.uploadArea.addEventListener('dragover', (e) => {
        e.preventDefault();
        DOMElements.uploadArea.style.borderColor = 'var(--accent-blue)';
    });

    DOMElements.uploadArea.addEventListener('dragleave', (e) => {
        e.preventDefault();
        DOMElements.uploadArea.style.borderColor = 'var(--border-color)';
    });

    DOMElements.uploadArea.addEventListener('drop', (e) => {
        e.preventDefault();
        DOMElements.uploadArea.style.borderColor = 'var(--border-color)';
        if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
            simulateImageUpload(e.dataTransfer.files[0]);
        }
    });
}

async function simulateImageUpload(file) {
    // Show loader
    DOMElements.uploadArea.classList.add('hidden');
    DOMElements.uploadStatus.classList.remove('hidden');

    // Set preview image
    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('preview-image').src = e.target.result;
    };
    reader.readAsDataURL(file);

    const formData = new FormData();
    formData.append('image', file);

    try {
        const response = await fetch('/api/upload-image', {
            method: 'POST',
            body: formData
        });

        const data = await response.json();

        if (response.ok && data.items) {
            // IF ONLY ONE ITEM FOUND: Search immediately (Direct product search)
            if (data.items.length === 1) {
                const item = data.items[0];
                closeImageUpload();
                navigate('results', { query: item.query });
                return;
            }

            DOMElements.uploadStatus.classList.add('hidden');
            document.getElementById('image-selection-area').classList.remove('hidden');

            // Render bounding boxes and chips
            const bbContainer = document.getElementById('bounding-boxes');
            const chipsContainer = document.getElementById('image-chips');
            bbContainer.innerHTML = '';
            chipsContainer.innerHTML = '';

            data.items.forEach(item => {
                // box is [ymin, xmin, ymax, xmax] out of 1000
                const [ymin, xmin, ymax, xmax] = item.box;
                const top = ymin / 10;
                const left = xmin / 10;
                const width = (xmax - xmin) / 10;
                const height = (ymax - ymin) / 10;

                // Draw Box
                const boxElem = document.createElement('div');
                boxElem.style.position = 'absolute';
                boxElem.style.top = `${top}%`;
                boxElem.style.left = `${left}%`;
                boxElem.style.width = `${width}%`;
                boxElem.style.height = `${height}%`;
                boxElem.style.border = '3px solid var(--accent-blue)';
                boxElem.style.borderRadius = '4px';
                boxElem.style.cursor = 'pointer';
                boxElem.style.pointerEvents = 'auto'; // allow click
                boxElem.style.backgroundColor = 'rgba(49, 130, 206, 0.15)';
                boxElem.style.boxShadow = '0 0 0 1px rgba(255,255,255,0.5)';
                boxElem.title = item.label;

                boxElem.onclick = () => {
                    closeImageUpload();
                    navigate('results', { query: item.query });
                };
                bbContainer.appendChild(boxElem);

                // Draw Chip Group
                const chipGroup = document.createElement('div');
                chipGroup.className = 'selection-chip-group';
                chipGroup.style.display = 'flex';
                chipGroup.style.flexDirection = 'column';
                chipGroup.style.gap = '8px';
                chipGroup.style.padding = '10px';
                chipGroup.style.backgroundColor = 'var(--bg-secondary)';
                chipGroup.style.borderRadius = '12px';
                chipGroup.style.border = '1px solid var(--border-color)';
                chipGroup.style.minWidth = '140px';

                const label = document.createElement('div');
                label.innerText = item.label;
                label.style.fontSize = '0.9rem';
                label.style.fontWeight = '700';
                label.style.color = 'var(--text-primary)';
                label.style.marginBottom = '4px';
                label.style.textAlign = 'center';
                chipGroup.appendChild(label);

                const btnGroup = document.createElement('div');
                btnGroup.style.display = 'flex';
                btnGroup.style.flexDirection = 'column';
                btnGroup.style.gap = '6px';

                const exactBtn = document.createElement('button');
                exactBtn.className = 'btn-primary';
                exactBtn.style.padding = '6px';
                exactBtn.style.fontSize = '0.8rem';
                exactBtn.innerHTML = `<i class="fa-solid fa-magnifying-glass"></i> หาแบรนด์นี้`;
                exactBtn.onclick = () => {
                    closeImageUpload();
                    navigate('results', { query: item.query });
                };
                btnGroup.appendChild(exactBtn);

                if (item.cheaper_query) {
                    const cheapBtn = document.createElement('button');
                    cheapBtn.className = 'btn-outline';
                    cheapBtn.style.padding = '6px';
                    cheapBtn.style.fontSize = '0.8rem';
                    cheapBtn.style.backgroundColor = 'var(--green-600)';
                    cheapBtn.style.color = 'white';
                    cheapBtn.style.borderColor = 'transparent';
                    cheapBtn.innerHTML = `<i class="fa-solid fa-tags"></i> แนวนี้ที่ถูกกว่า`;
                    cheapBtn.onclick = () => {
                        closeImageUpload();
                        navigate('results', { query: item.cheaper_query });
                    };
                    btnGroup.appendChild(cheapBtn);
                }

                chipGroup.appendChild(btnGroup);
                chipsContainer.appendChild(chipGroup);
            });

        } else {
            alert(data.error || "ไม่สามารถวิเคราะห์รูปภาพได้");
            closeImageUpload();
        }
    } catch (error) {
        console.error("Image Upload Error:", error);
        alert("เกิดข้อผิดพลาดในการเชื่อมต่อเซิร์ฟเวอร์");
        closeImageUpload();
    }
}

// --- Authentication & History Flow ---

let authMode = 'login'; // 'login' or 'register'

function openAuthModal() {
    authMode = 'login';
    document.getElementById('auth-title').innerText = 'เข้าสู่ระบบ';
    document.getElementById('auth-submit-btn').innerText = 'เข้าสู่ระบบ';
    document.getElementById('auth-toggle-text').innerHTML = 'ยังไม่มีบัญชี? <a href="#" onclick="toggleAuthMode()" style="color: var(--blue-500); text-decoration: none;">สมัครสมาชิก</a>';
    document.getElementById('auth-error').style.display = 'none';
    document.getElementById('auth-username').value = '';
    document.getElementById('auth-password').value = '';
    document.getElementById('auth-modal').classList.remove('hidden');
}

function closeAuthModal() {
    document.getElementById('auth-modal').classList.add('hidden');
}

function toggleAuthMode() {
    if (authMode === 'login') {
        authMode = 'register';
        document.getElementById('auth-title').innerText = 'สมัครสมาชิกใหม่';
        document.getElementById('auth-submit-btn').innerText = 'สมัครสมาชิก';
        document.getElementById('auth-toggle-text').innerHTML = 'มีบัญชีอยู่แล้ว? <a href="#" onclick="toggleAuthMode()" style="color: var(--blue-500); text-decoration: none;">เข้าสู่ระบบ</a>';
    } else {
        authMode = 'login';
        document.getElementById('auth-title').innerText = 'เข้าสู่ระบบ';
        document.getElementById('auth-submit-btn').innerText = 'เข้าสู่ระบบ';
        document.getElementById('auth-toggle-text').innerHTML = 'ยังไม่มีบัญชี? <a href="#" onclick="toggleAuthMode()" style="color: var(--blue-500); text-decoration: none;">สมัครสมาชิก</a>';
    }
}

async function handleAuthSubmit() {
    const user = document.getElementById('auth-username').value.trim();
    const pass = document.getElementById('auth-password').value.trim();
    const errObj = document.getElementById('auth-error');

    if (!user || !pass) {
        errObj.innerText = 'กรุณากรอกข้อมูลให้ครบถ้วน';
        errObj.style.display = 'block';
        return;
    }

    const endpoint = authMode === 'login' ? '/api/login' : '/api/register';

    try {
        const res = await fetch(endpoint, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username: user, password: pass })
        });
        const data = await res.json();

        if (!res.ok) {
            errObj.innerText = data.error || 'เกิดข้อผิดพลาด';
            errObj.style.display = 'block';
        } else {
            if (authMode === 'register') {
                // Auto login after register or just switch to login mode safely
                authMode = 'login';
                await handleAuthSubmit(); // recursively login
            } else {
                appState.auth.loggedIn = true;
                appState.auth.username = data.username;
                closeAuthModal();
                renderNavActions();
            }
        }
    } catch (e) {
        errObj.innerText = 'เซิร์ฟเวอร์มีปัญหา กรุณาลองใหม่';
        errObj.style.display = 'block';
    }
}

async function checkAuth() {
    try {
        const res = await fetch('/api/user');
        const data = await res.json();
        appState.auth.loggedIn = data.logged_in;
        appState.auth.username = data.username;
    } catch (e) {
        appState.auth.loggedIn = false;
    }
}

async function handleLogout() {
    await fetch('/api/logout', { method: 'POST' });
    appState.auth.loggedIn = false;
    appState.auth.username = null;
    renderNavActions();
    document.getElementById('history-sidebar').classList.add('hidden');
}

function renderNavActions() {
    const navActions = document.getElementById('nav-actions');
    if (!navActions) return;

    if (appState.auth.loggedIn) {
        navActions.innerHTML = `
            <div style="display: flex; gap: 1rem; align-items: center;">
                <span style="font-weight: 600; color: var(--text-primary);"><i class="fa-solid fa-user-circle"></i> ${appState.auth.username}</span>
                <button class="btn-outline" onclick="toggleHistory()"><i class="fa-solid fa-clock-rotate-left"></i> ประวัติ</button>
                <button class="back-btn" onclick="handleLogout()" title="ออกจากระบบ" style="color: var(--red-500);"><i class="fa-solid fa-right-from-bracket"></i></button>
            </div>
        `;
    } else {
        navActions.innerHTML = `
            <button class="btn-primary" onclick="openAuthModal()" style="padding: 0.5rem 1rem;">เข้าสู่ระบบ</button>
        `;
    }
}

// --- History Sidebar ---

async function toggleHistory() {
    const sidebar = document.getElementById('history-sidebar');
    const isHidden = sidebar.classList.contains('hidden');

    if (isHidden) {
        sidebar.classList.remove('hidden');
        await renderHistory();
    } else {
        sidebar.classList.add('hidden');
    }
}

async function renderHistory() {
    const listBody = document.getElementById('history-list');
    listBody.innerHTML = '<div class="loader"></div>';

    try {
        const res = await fetch('/api/history');
        if (!res.ok) {
            listBody.innerHTML = '<p style="text-align:center; color: var(--text-secondary);">กรุณาเข้าสู่ระบบก่อน</p>';
            return;
        }

        const historyData = await res.json();
        if (historyData.length === 0) {
            listBody.innerHTML = '<p style="text-align:center; color: var(--text-secondary);">ยังไม่มีประวัติการค้นหา</p>';
            return;
        }

        listBody.innerHTML = historyData.map(query => `
            <div class="history-item" onclick="toggleHistory(); handleSearch('${query}')">
                <i class="fa-solid fa-magnifying-glass" style="color: var(--text-secondary); margin-right: 8px;"></i> ${query}
            </div>
        `).join('');
    } catch (e) {
        listBody.innerHTML = '<p style="text-align:center; color: var(--text-secondary);">ไม่สามารถดึงข้อมูลได้</p>';
    }
}

// Boot
document.addEventListener('DOMContentLoaded', init);
