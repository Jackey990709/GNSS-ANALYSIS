document.addEventListener('DOMContentLoaded', init);

let config = null;
let summaryData = null;
let sceneStats = {}; // 缓存各场景数据

// 导出CSV功能
window.exportTableToCSV = function(tableId, filename) {
    const table = document.getElementById(tableId);
    if (!table) {
        alert('Table not found: ' + tableId);
        return;
    }

    const rows = table.querySelectorAll('tr');
    let csv = [];
    
    // 添加 UTF-8 BOM 以支持 Excel 打开中文
    csv.push('\uFEFF'); 

    for (const row of rows) {
        // 只导出可见行
        if (row.style.display === 'none') continue;
        
        const cols = row.querySelectorAll('td, th');
        const rowData = [];
        
        for (const col of cols) {
            // 清理文本：移除换行符，处理双引号
            // 针对表头中的 <br>，将其替换为空格
            let text = col.innerHTML.replace(/<br\s*\/?>/gi, ' ');
            // 创建临时元素来获取纯文本
            const temp = document.createElement('div');
            temp.innerHTML = text;
            let data = temp.textContent || temp.innerText || '';
            
            // 移除多余空白
            data = data.replace(/(\r\n|\n|\r)/gm, '').trim();
            
            // 处理空数据 "-"
            if (data === '-' || data === '') {
                data = '-';
            }
            
            // 处理CSV转义：双引号变成两个双引号
            data = data.replace(/"/g, '""');
            
            rowData.push(`"${data}"`);
        }
        
        // 忽略空行
        if (rowData.length > 0) {
            csv.push(rowData.join(','));
        }
    }
    
    const blob = new Blob([csv.join('\n')], { type: 'text/csv;charset=utf-8;' });
    const link = document.createElement('a');
    
    if (navigator.msSaveBlob) { // IE 10+
        navigator.msSaveBlob(blob, filename);
    } else {
        const url = URL.createObjectURL(blob);
        link.setAttribute('href', url);
        link.setAttribute('download', filename);
        link.style.visibility = 'hidden';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }
};

// 辅助函数：格式化数值，空值返回 "-"
function formatValue(val) {
    if (val === null || val === undefined || val === '') return '-';
    return val;
}

async function init() {
    try {
        // Check if reportData is available
        if (!window.reportData) {
            throw new Error("Report data not found. Please ensure data/report_data.js is loaded.");
        }
        
        // 1. Load config and summary from global variable
        config = window.reportData.config;
        summaryData = window.reportData.summary;
        
        // 2. 渲染静态部分
        renderTestMeta();
        
        // 3. 动态加载并渲染每个场景
        const scenesContainer = document.getElementById('scenes-container');
        const navList = document.getElementById('nav-list');
        const conclusionLink = navList.lastElementChild; // "结论与建议"
        
        for (const scene of config.scenes) {
            // 预先获取数据以判断功能开关
            
            let stats = window.reportData.scenes ? window.reportData.scenes[scene.id] : null;
            const showCn0 = hasValidCn0Data(stats);

            // 添加导航项
            const navItem = document.createElement('li');
            navItem.innerHTML = `
                <a href="#section-scene-${scene.id}">${scene.name}</a>
                <ul class="sub-nav">
                    ${showCn0 ? `<li><a href="#section-scene-${scene.id}-cn0">信号质量 (CN0)</a></li>` : ''}
                    <li><a href="#section-scene-${scene.id}-status">定位状态分布</a></li>
                    <li><a href="#section-scene-${scene.id}-cep">CEP 误差表</a></li>
                    <li><a href="#section-scene-${scene.id}-bar">CEP 精度柱状图</a></li>
                    <li><a href="#section-scene-${scene.id}-error">误差图</a></li>
                    <li><a href="#section-scene-${scene.id}-track">轨迹回放</a></li>
                </ul>
            `;
            navList.appendChild(navItem);
            
            // 加载该场景数据
            try {
                if (!stats) {
                     throw new Error(`Stats not found for scene ${scene.id}`);
                }
                sceneStats[scene.id] = stats;
                
                // 渲染场景内容
                const sceneSection = createSceneSection(scene, stats);
                scenesContainer.appendChild(sceneSection);
            } catch (err) {
                console.error(`Failed to load stats for ${scene.id}`, err);
                const errDiv = document.createElement('div');
                errDiv.className = 'card';
                errDiv.innerHTML = `<h3>${scene.name}</h3><p style="color:red">数据加载失败</p>`;
                scenesContainer.appendChild(errDiv);
            }

            // break;
        }
        
        // 4. 渲染总览部分（现在sceneStats已填充）
        renderSummarySection();
        
        // 5. 激活导航滚动监听
        initScrollSpy();

        // 6. 初始化图片查看器
        initImageViewer();
        
        // 7. 初始化侧边栏切换
        initSidebarToggle();
        
    } catch (err) {
        console.error('Initialization failed', err);
        document.body.innerHTML = `<h1 style="color:red; padding:20px">报告加载失败：${err.message}</h1><p style="padding:20px">请确保 data/report_data.js 文件存在</p>`;
    }
}

function initImageViewer() {
    const modal = document.getElementById('image-modal');
    const modalImg = document.getElementById('modal-img');
    const captionText = document.getElementById('modal-caption');
    const closeBtn = document.querySelector('.modal-close');
    const zoomInBtn = document.getElementById('zoom-in');
    const zoomOutBtn = document.getElementById('zoom-out');
    const zoomResetBtn = document.getElementById('zoom-reset');

    let currentScale = 1;
    let isDragging = false;
    let startX, startY, translateX = 0, translateY = 0;

    // 更新图片变换
    function updateTransform() {
        modalImg.style.transform = `translate(${translateX}px, ${translateY}px) scale(${currentScale})`;
    }

    // 重置状态
    function resetZoom() {
        currentScale = 1;
        translateX = 0;
        translateY = 0;
        updateTransform();
    }

    // 委托监听所有 .chart-item 内的图片点击
    document.body.addEventListener('click', (e) => {
        if (e.target.tagName === 'IMG' && e.target.closest('.chart-item')) {
            modal.style.display = "flex"; // 使用flex布局居中
            modalImg.src = e.target.src;
            captionText.innerHTML = e.target.alt;
            resetZoom();
        }
    });

    // 缩放控制
    zoomInBtn.onclick = (e) => {
        e.stopPropagation();
        currentScale += 0.2;
        updateTransform();
    };

    zoomOutBtn.onclick = (e) => {
        e.stopPropagation();
        if (currentScale > 0.4) {
            currentScale -= 0.2;
            updateTransform();
        }
    };

    zoomResetBtn.onclick = (e) => {
        e.stopPropagation();
        resetZoom();
    };

    // 滚轮缩放
    modalImg.addEventListener('wheel', (e) => {
        e.preventDefault();
        const delta = e.deltaY > 0 ? -0.1 : 0.1;
        const newScale = currentScale + delta;
        if (newScale > 0.2 && newScale < 5) {
            currentScale = newScale;
            updateTransform();
        }
    });

    // 拖拽功能
    modalImg.addEventListener('mousedown', (e) => {
        isDragging = true;
        startX = e.clientX - translateX;
        startY = e.clientY - translateY;
        e.preventDefault(); // 防止默认拖拽行为
    });

    document.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        translateX = e.clientX - startX;
        translateY = e.clientY - startY;
        updateTransform();
    });

    document.addEventListener('mouseup', () => {
        isDragging = false;
    });

    // 关闭按钮
    closeBtn.onclick = function() {
        modal.style.display = "none";
    }

    // 点击背景关闭
    modal.onclick = function(e) {
        if (e.target === modal || e.target.classList.contains('modal-content-wrapper')) {
            modal.style.display = "none";
        }
    }

    // ESC键关闭
    document.addEventListener('keydown', (e) => {
        if (e.key === "Escape" && modal.style.display === "flex") {
            modal.style.display = "none";
        }
    });
}

function initSidebarToggle() {
    const toggleBtn = document.getElementById('sidebar-toggle');
    const sidebar = document.getElementById('sidebar');
    const content = document.getElementById('content');
    
    if (toggleBtn && sidebar && content) {
        toggleBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            content.classList.toggle('expanded');
            document.body.classList.toggle('sidebar-collapsed');
        });
    }
}

function renderTestMeta() {
    const container = document.getElementById('test-meta');
    const deviceNames = config.devices.join(', ');
    const sceneNames = config.scenes.map(s => s.name).join(', ');
    
    container.innerHTML = `
        <div class="meta-grid">
            <div class="meta-item">
                <span class="meta-label">测试设备</span>
                <span class="meta-value">${deviceNames}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">测试场景</span>
                <span class="meta-value">${sceneNames}</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">报告生成时间</span>
                <span class="meta-value">${new Date().toLocaleDateString()}</span>
            </div>
        </div>
    `;
}

function renderSummarySection() {
    const container = document.getElementById('summary-container');
    
    // 创建一个包含所有指标的详细表格
    let tableHTML = `
        <div class="card">
            <div id="quality-filters" class="quality-filters">
                <label>表格数据筛选（基于定位质量）：</label>
                <label><input type="checkbox" class="quality-checkbox" value="0"> 0</label>
                <label><input type="checkbox" class="quality-checkbox" value="1"> 1</label>
                <label><input type="checkbox" class="quality-checkbox" value="2"> 2</label>
                <label><input type="checkbox" class="quality-checkbox" value="4"> 4</label>
                <label><input type="checkbox" class="quality-checkbox" value="5"> 5</label>
                <label><input type="checkbox" class="quality-checkbox" value="6"> 6</label>
                <label><input type="checkbox" class="quality-checkbox" value="all" checked> all</label>
                <button class="btn-export" onclick="exportTableToCSV('summary-table', 'gnss_summary_report.csv')">
                    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    导出CSV
                </button>
            </div>
            <div class="table-responsive">
                <table id="summary-table">
                <thead>
                    <tr>
                        <th>场景</th>
                        <th>设备名</th>
                        <th>定位质量</th>
                        <th>定位点数</th>
                        <th>占比</th>
                        <th>水平<br>CEP50</th>
                        <th>水平<br>CEP68</th>
                        <th>水平<br>CEP95</th>
                        <th>水平<br>CEP99</th>
                        <th>水平<br>CEP100</th>
                        <th>高程<br>CEP50</th>
                        <th>高程<br>CEP68</th>
                        <th>高程<br>CEP95</th>
                        <th>高程<br>CEP99</th>
                        <th>高程<br>CEP100</th>
                        <th>速度<br>CEP50</th>
                        <th>速度<br>CEP68</th>
                        <th>速度<br>CEP95</th>
                        <th>速度<br>CEP99</th>
                        <th>速度<br>CEP100</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // 定义场景背景颜色类
    const sceneColors = {
        "open_sky": "scene-open-sky",
        "tree_shade": "scene-tree-shade",
        "urban_canyon": "scene-urban-canyon",
        "highway": "scene-highway",
        "elevated": "scene-elevated",
        "tunnel": "scene-tunnel"
    };
    
    for (const scene of config.scenes) {
        const sceneKey = scene.id;
        const colorClass = sceneColors[sceneKey] || "";
        
        if (summaryData.scenes && summaryData.scenes[sceneKey]) {
            for (const dev of config.devices) {
                const devSummaryData = summaryData.scenes[sceneKey][dev];
                
                if (devSummaryData) {
                    // 获取设备的总定位点数 (使用Total_Points，如果不存在则回退到all.points)
                    const allDataEntry = devSummaryData["all"];
                    // 优先使用 total_epochs (总历元数)，如果没有则尝试计算所有质量点的和
                    let totalPoints = allDataEntry?.total_epochs;
                    
                    if (!totalPoints) {
                        // 如果后端没有传total_epochs，尝试累加
                        let sum = 0;
                        for (const q in devSummaryData) {
                             if (q !== 'all') sum += devSummaryData[q].points;
                        }
                        // 如果累加为0（可能是空数据），则回退到all.points
                        totalPoints = sum > 0 ? sum : (allDataEntry?.points || 0);
                    }
                    
                    // 遍历所有定位质量级别
                    for (const quality in devSummaryData) {
                        if (quality === "all") continue; // 跳过all，最后单独处理
                        
                        const qualityData = devSummaryData[quality];
                        if (qualityData) {
                            // 计算该定位质量级别的占比
                            const qualityRatio = totalPoints > 0 ? (qualityData.points / totalPoints * 100).toFixed(1) + "%" : "0%";
                            
                            tableHTML += `
                                <tr class="${colorClass}" data-quality="${quality}">
                                    <td class="scene-name-cell"><strong>${scene.name}</strong></td>
                                    <td>${dev}</td>
                                    <td>${quality}</td>
                                    <td>${qualityData.points}</td>
                                    <td>${qualityRatio}</td>
                                    <td>${formatValue(qualityData.horz_cep50)}</td>
                                    <td>${formatValue(qualityData.horz_cep68)}</td>
                                    <td>${formatValue(qualityData.horz_cep95)}</td>
                                    <td>${formatValue(qualityData.horz_cep99)}</td>
                                    <td>${formatValue(qualityData.horz_cep100)}</td>
                                    <td>${formatValue(qualityData.vert_cep50)}</td>
                                    <td>${formatValue(qualityData.vert_cep68)}</td>
                                    <td>${formatValue(qualityData.vert_cep95)}</td>
                                    <td>${formatValue(qualityData.vert_cep99)}</td>
                                    <td>${formatValue(qualityData.vert_cep100)}</td>
                                    <td>${formatValue(qualityData.speed_cep50)}</td>
                                    <td>${formatValue(qualityData.speed_cep68)}</td>
                                    <td>${formatValue(qualityData.speed_cep95)}</td>
                                    <td>${formatValue(qualityData.speed_cep99)}</td>
                                    <td>${formatValue(qualityData.speed_cep100)}</td>
                                </tr>
                            `;
                        }
                    }
                    
                    // 处理all定位质量级别
                    const allData = devSummaryData["all"];
                    if (allData) {
                        const allRatio = totalPoints > 0 ? (allData.points / totalPoints * 100).toFixed(1) + "%" : "0%";
                        tableHTML += `
                            <tr class="${colorClass}" data-quality="all">
                                <td class="scene-name-cell"><strong>${scene.name}</strong></td>
                                <td>${dev}</td>
                                <td>all</td>
                                <td>${allData.points}</td>
                                <td>${allRatio}</td>
                                <td>${formatValue(allData.horz_cep50)}</td>
                                <td>${formatValue(allData.horz_cep68)}</td>
                                <td>${formatValue(allData.horz_cep95)}</td>
                                <td>${formatValue(allData.horz_cep99)}</td>
                                <td>${formatValue(allData.horz_cep100)}</td>
                                <td>${formatValue(allData.vert_cep50)}</td>
                                <td>${formatValue(allData.vert_cep68)}</td>
                                <td>${formatValue(allData.vert_cep95)}</td>
                                <td>${formatValue(allData.vert_cep99)}</td>
                                <td>${formatValue(allData.vert_cep100)}</td>
                                <td>${formatValue(allData.speed_cep50)}</td>
                                <td>${formatValue(allData.speed_cep68)}</td>
                                <td>${formatValue(allData.speed_cep95)}</td>
                                <td>${formatValue(allData.speed_cep99)}</td>
                                <td>${formatValue(allData.speed_cep100)}</td>
                            </tr>
                        `;
                    }
                }
            }
        }
    }
    
    tableHTML += `</tbody></table></div></div>`;
    container.innerHTML = tableHTML;
    
    // 添加复选框筛选功能
    addQualityFilterListener();
}

// 添加定位质量筛选事件监听
function addQualityFilterListener() {
    // 为每个表格添加筛选功能
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        const filtersContainer = card.querySelector('.quality-filters');
        // 支持单个 card 内多个 table 的情况
        const tables = card.querySelectorAll('table');
        
        if (filtersContainer && tables.length > 0) {
            // 初始化显示：只显示all质量级别的行
            tables.forEach(table => {
                const tableRows = table.querySelectorAll('tbody tr');
                tableRows.forEach(row => {
                    const quality = row.getAttribute('data-quality');
                    if (quality === 'all') {
                        row.style.display = '';
                    } else {
                        row.style.display = 'none';
                    }
                });
            });
            
            // 添加事件监听
            filtersContainer.addEventListener('change', (e) => {
                if (e.target.classList.contains('quality-checkbox')) {
                    // 获取所有选中的质量级别
                    const checkedQualities = Array.from(filtersContainer.querySelectorAll('.quality-checkbox:checked'))
                        .map(checkbox => checkbox.value);
                    
                    // 根据选中的质量级别显示或隐藏行（遍历所有表格）
                    tables.forEach(table => {
                        const tableRows = table.querySelectorAll('tbody tr');
                        tableRows.forEach(row => {
                            const quality = row.getAttribute('data-quality');
                            if (checkedQualities.includes(quality)) {
                                row.style.display = '';
                            } else {
                                row.style.display = 'none';
                            }
                        });
                    });
                }
            });
        }
    });
}

function hasValidCn0Data(stats) {
    if (!stats || !stats.device_stats) return false;
    for (const dev in stats.device_stats) {
        const devStats = stats.device_stats[dev];
        if (devStats && devStats.cn0_stats) {
            // Check recursively for any valid data
            if (checkCn0Object(devStats.cn0_stats)) return true;
        }
    }
    return false;
}

function checkCn0Object(obj) {
    for (const key in obj) {
        const val = obj[key];
        if (val && typeof val === 'object') {
             // Check if it's a leaf node with mean/avg/max
             if ((val.mean > 0) || (val.avg > 0) || (val.max > 0)) return true;
             // Otherwise recurse
             if (checkCn0Object(val)) return true;
        }
    }
    return false;
}

function createSceneSection(scene, stats) {
    const section = document.createElement('section');
    section.id = `section-scene-${scene.id}`;
    
    // 场景标题
    
    // 场景时间范围
    let timeStr = "全程";
    if (scene.begin_time && scene.end_time) {
        timeStr = `${scene.begin_time} - ${scene.end_time}`;
    } else {
         // 如果没有具体时间，尝试生成一个默认的或者保留"全程"
         // 之前的随机逻辑已移除，因为用户明确要求使用场景时间
    }
    
    // 报告生成时间
    const reportGenTime = new Date().toLocaleString();
    
    // 计算场景难度（已删除）
    let difficultyHTML = '';

    let html = `
        <h2>
            ${scene.name}
            ${difficultyHTML}
        </h2>
        <p class="scene-time" style="color: #666; margin-top: -10px; margin-bottom: 20px; font-size: 0.9em;">
            <span style="display: inline-flex; align-items: center; gap: 5px; margin-right: 20px;">
                <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>
                测试时间：${timeStr}
            </span>
            <span style="display: inline-flex; align-items: center; gap: 5px;">
                <svg viewBox="0 0 24 24" width="14" height="14" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg>
                报告生成时间：${reportGenTime}
            </span>
        </p>
    `;
    
    // 1. 信号质量与定位状态分布
    const showCn0 = hasValidCn0Data(stats);
    
    html += `<div style="margin-bottom: 30px;">`;

    if (showCn0) {
        html += `
            <!-- 信号质量 (CN0) -->
            <div class="card" style="margin-bottom: 20px;">
                <div class="card-title">
                    <h3 id="section-scene-${scene.id}-cn0" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">信号质量分析 (CN0) 📡</h3>
                    <div class="cn0-controls" style="font-family: var(--font-sans); font-size: 0.9rem; font-weight: normal;">
                        <label style="margin-right: 15px; cursor: pointer;">
                            <input type="radio" name="cn0-mode-${scene.id}" value="mean" checked onchange="updateCn0Mode('${scene.id}', 'mean')"> Mean CN0
                        </label>
                        <label style="cursor: pointer;">
                            <input type="radio" name="cn0-mode-${scene.id}" value="max" onchange="updateCn0Mode('${scene.id}', 'max')"> Max CN0
                        </label>
                    </div>
                </div>
                <div class="table-responsive">
                <table class="cn0-table" id="cn0-table-${scene.id}" style="font-size: 0.85rem;">
                    <thead>
                        <tr>
                            <th rowspan="2" style="min-width:80px; position:sticky; left:0; z-index:10; background:var(--secondary-color); color:white; border-right:2px solid #ddd;">
                                设备<br>
                                <span class="cn0-mode-label" style="font-size:0.7em; font-weight:normal;">(Mean)</span>
                            </th>
                            <th colspan="3">GPS</th>
                            <th colspan="5">BeiDou</th>
                            <th colspan="4">Galileo</th>
                            <th colspan="3">GLONASS</th>
                            <th colspan="4">QZSS</th>
                            <th colspan="2">IRNSS</th>
                        </tr>
                        <tr>
                            <th title="GPS L1">L1</th><th title="GPS L2">L2</th><th title="GPS L5">L5</th>
                            <th title="BDS B1I">B1I</th><th title="BDS B1C">B1C</th><th title="BDS B2a">B2a</th><th title="BDS B2b">B2b</th><th title="BDS B3I">B3I</th>
                            <th title="GAL E1">E1</th><th title="GAL E5a">E5a</th><th title="GAL E5b">E5b</th><th title="GAL E6">E6</th>
                            <th title="GLO G1">G1</th><th title="GLO G2">G2</th><th title="GLO G3">G3</th>
                            <th title="QZSS L1">L1</th><th title="QZSS L2">L2</th><th title="QZSS L5">L5</th><th title="QZSS L6">L6</th>
                            <th title="IRNSS L5">L5</th><th title="IRNSS S">S</th>
                        </tr>
                    </thead>
                    <tbody>
                        ${config.devices.map(dev => {
                            const devStat = stats.device_stats[dev];
                            if (!devStat || !devStat.cn0_stats) return '';
                            
                            const targetBands = [
                                "GPS_L1", "GPS_L2", "GPS_L5",
                                "BDS_B1I", "BDS_B1C", "BDS_B2a", "BDS_B2b", "BDS_B3I",
                                "GAL_E1", "GAL_E5a", "GAL_E5b", "GAL_E6",
                                "GLO_G1", "GLO_G2", "GLO_G3",
                                "QZSS_L1", "QZSS_L2", "QZSS_L5", "QZSS_L6",
                                "IRNSS_L5", "IRNSS_S"
                            ];
                            
                            // 第一列：设备名（固定）
                            let rowHtml = `<td style="position:sticky; left:0; z-index:10; background:white; border-right:2px solid #ddd;"><strong>${dev}</strong></td>`;
                            
                            targetBands.forEach(band => {
                                let bandData = null;
                                
                                // 1. Try direct access (Flat structure)
                                if (devStat.cn0_stats[band]) {
                                    bandData = devStat.cn0_stats[band];
                                } 
                                // 2. Try nested structure
                                else {
                                    const parts = band.split('_');
                                    if (parts.length >= 2) {
                                        let sys = parts[0];
                                        let sig = parts.slice(1).join('_');
                                        
                                        // Mapping
                                        const sysMap = {
                                            "BDS": "BEIDOU",
                                            "GAL": "GALILEO",
                                            "GLO": "GLONASS",
                                            "QZSS": "QZSS",
                                            "IRNSS": "IRNSS",
                                            "GPS": "GPS",
                                            "SBAS": "SBAS"
                                        };
                                        const pySys = sysMap[sys] || sys;
                                        
                                        if (devStat.cn0_stats[pySys] && devStat.cn0_stats[pySys][sig]) {
                                            bandData = devStat.cn0_stats[pySys][sig];
                                        }
                                    }
                                }

                                if (bandData) {
                                    // Normalize mean/avg
                                    const meanVal = bandData.mean !== undefined ? bandData.mean : (bandData.avg !== undefined ? bandData.avg : 0);
                                    const maxVal = bandData.max || 0;
                                    
                                    // 存储 mean 和 max 到 data 属性
                                    rowHtml += `<td class="cn0-cell" data-mean="${meanVal}" data-max="${maxVal}" title="${band}\nMean: ${meanVal}\nMax: ${maxVal}">${meanVal}</td>`;
                                } else {
                                    rowHtml += `<td class="cn0-cell" style="color:#ccc;">-</td>`;
                                }
                            });
                            
                            return `<tr>${rowHtml}</tr>`;
                        }).join('')}
                    </tbody>
                </table>
                </div>
            </div>
        `;
    }
            
    html += `
            <!-- 定位状态分布 -->
            <div class="card" style="margin-bottom: 0;">
                <div class="card-title">
                    <h3 id="section-scene-${scene.id}-status" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">定位状态分布 🥧</h3>
                </div>
                <div class="legend-container" style="margin-bottom: 10px;">
                    <div class="legend-item"><span class="legend-color bg-q5"></span>Fixed</div>
                    <div class="legend-item"><span class="legend-color bg-q4"></span>Float</div>
                    <div class="legend-item"><span class="legend-color bg-q2"></span>DGPS</div>
                    <div class="legend-item"><span class="legend-color bg-q1"></span>Single</div>
                    <div class="legend-item"><span class="legend-color bg-q0"></span>None</div>
                </div>
                <div class="table-responsive">
                    <table class="status-table" style="width: 100%; margin-bottom: 0;">
                        <thead>
                            <tr>
                                <th style="width: 200px;">设备</th>
                                <th>状态分布</th>
                            </tr>
                        </thead>
                        <tbody>
                        ${config.devices.map(dev => {
                            const devStat = stats.device_stats[dev];
                            if (!devStat) return '';
                            const counts = devStat.quality_counts;
                            // 使用 total_epochs 作为分母，如果不存在则使用 all
                            const total = counts.total_epochs || counts.all || 1; // avoid divide by zero
                            
                            // Calculate percentages
                            // 确保总和为100%，消除浮点数误差
                            let p5 = (counts['5'] || 0) / total * 100;
                            let p4 = (counts['4'] || 0) / total * 100;
                            let p2 = (counts['2'] || 0) / total * 100;
                            let p1 = (counts['1'] || 0) / total * 100;
                            let p0 = (counts['0'] || 0) / total * 100;
                            
                            // 保留一位小数显示用
                            const d5 = p5.toFixed(1);
                            const d4 = p4.toFixed(1);
                            const d2 = p2.toFixed(1);
                            const d1 = p1.toFixed(1);
                            const d0 = p0.toFixed(1);
    
                            return `
                                <tr>
                                    <td style="font-weight: bold;">${dev}</td>
                                    <td style="vertical-align: middle; padding: 8px;">
                                        <div class="stacked-bar" style="height: 24px; display: flex; width: 100%; background: #eee; border-radius: 4px;">
                                            ${p5 > 0 ? `<div class="bar-segment bg-q5" style="width: ${p5}%" data-tooltip="Fixed: ${d5}%"></div>` : ''}
                                            ${p4 > 0 ? `<div class="bar-segment bg-q4" style="width: ${p4}%" data-tooltip="Float: ${d4}%"></div>` : ''}
                                            ${p2 > 0 ? `<div class="bar-segment bg-q2" style="width: ${p2}%" data-tooltip="DGPS: ${d2}%"></div>` : ''}
                                            ${p1 > 0 ? `<div class="bar-segment bg-q1" style="width: ${p1}%" data-tooltip="Single: ${d1}%"></div>` : ''}
                                            ${p0 > 0 ? `<div class="bar-segment bg-q0" style="width: ${p0}%" data-tooltip="None: ${d0}%"></div>` : ''}
                                        </div>
                                    </td>
                                </tr>
                            `;
                        }).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    `;

    // CEP误差表格
    html += `
        <div class="card">
            <div class="card-title">
                <h3 id="section-scene-${scene.id}-cep" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">CEP 误差表</h3>
            </div>
            <div class="quality-filters">
                <label>定位质量筛选：</label>
                <label><input type="checkbox" class="quality-checkbox" value="0"> 0</label>
                <label><input type="checkbox" class="quality-checkbox" value="1"> 1</label>
                <label><input type="checkbox" class="quality-checkbox" value="2"> 2</label>
                <label><input type="checkbox" class="quality-checkbox" value="4"> 4</label>
                <label><input type="checkbox" class="quality-checkbox" value="5"> 5</label>
                <label><input type="checkbox" class="quality-checkbox" value="6"> 6</label>
                <label><input type="checkbox" class="quality-checkbox" value="all" checked> all</label>
                <button class="btn-export" onclick="exportTableToCSV('scene-table-${scene.id}', '${scene.id}_cep_report.csv')">
                    <svg viewBox="0 0 24 24" width="16" height="16" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path><polyline points="7 10 12 15 17 10"></polyline><line x1="12" y1="15" x2="12" y2="3"></line></svg>
                    导出CSV
                </button>
            </div>
            <div class="table-responsive">
                <table id="scene-table-${scene.id}" class="scene-table">
                <thead>
                    <tr>
                        <th>场景</th>
                        <th>设备名</th>
                        <th>定位质量</th>
                        <th>定位点数</th>
                        <th>占比</th>
                        <th>水平<br>CEP50</th>
                        <th>水平<br>CEP68</th>
                        <th>水平<br>CEP95</th>
                        <th>水平<br>CEP99</th>
                        <th>水平<br>CEP100</th>
                        <th>高程<br>CEP50</th>
                        <th>高程<br>CEP68</th>
                        <th>高程<br>CEP95</th>
                        <th>高程<br>CEP99</th>
                        <th>高程<br>CEP100</th>
                        <th>速度<br>CEP50</th>
                        <th>速度<br>CEP68</th>
                        <th>速度<br>CEP95</th>
                        <th>速度<br>CEP99</th>
                        <th>速度<br>CEP100</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    // 获取该场景下的所有设备数据
    const sceneSummaryData = summaryData.scenes[scene.id];
    
    if (sceneSummaryData) {
        for (const dev of config.devices) {
            const devData = sceneSummaryData[dev];
            if (devData) {
                // 定义场景背景颜色类
                const sceneColors = {
                    "open_sky": "scene-open-sky",
                    "tree_shade": "scene-tree-shade",
                    "urban_canyon": "scene-urban-canyon",
                    "highway": "scene-highway",
                    "elevated": "scene-elevated",
                    "tunnel": "scene-tunnel"
                };
                
                const colorClass = sceneColors[scene.id] || "";
                
                // 计算总点数 (使用Total_Points，如果不存在则回退到all.points)
                const allDataEntry = devData["all"];
                // 优先使用 total_epochs (总历元数)，如果没有则尝试计算所有质量点的和
                let totalPoints = allDataEntry?.total_epochs;
                
                if (!totalPoints) {
                    // 如果后端没有传total_epochs，尝试累加
                    let sum = 0;
                    for (const q in devData) {
                         if (q !== 'all') sum += devData[q].points;
                    }
                    // 如果累加为0（可能是空数据），则回退到all.points
                    totalPoints = sum > 0 ? sum : (allDataEntry?.points || 0);
                }
                
                // 遍历所有定位质量级别
                for (const quality in devData) {
                    if (quality === "all") continue; // 跳过all，最后单独处理
                    
                    const qualityData = devData[quality];
                    if (qualityData) {
                        // 计算占比
                        const qualityRatio = totalPoints > 0 ? (qualityData.points / totalPoints * 100).toFixed(1) + "%" : "0%";
                        
                        html += `
                            <tr class="${colorClass}" data-quality="${quality}">
                                <td><strong>${scene.name}</strong></td>
                                <td>${dev}</td>
                                <td>${quality}</td>
                                <td>${qualityData.points}</td>
                                <td>${qualityRatio}</td>
                                <td>${formatValue(qualityData.horz_cep50)}</td>
                                <td>${formatValue(qualityData.horz_cep68)}</td>
                                <td>${formatValue(qualityData.horz_cep95)}</td>
                                <td>${formatValue(qualityData.horz_cep99)}</td>
                                <td>${formatValue(qualityData.horz_cep100)}</td>
                                <td>${formatValue(qualityData.vert_cep50)}</td>
                                <td>${formatValue(qualityData.vert_cep68)}</td>
                                <td>${formatValue(qualityData.vert_cep95)}</td>
                                <td>${formatValue(qualityData.vert_cep99)}</td>
                                <td>${formatValue(qualityData.vert_cep100)}</td>
                                <td>${formatValue(qualityData.speed_cep50)}</td>
                                <td>${formatValue(qualityData.speed_cep68)}</td>
                                <td>${formatValue(qualityData.speed_cep95)}</td>
                                <td>${formatValue(qualityData.speed_cep99)}</td>
                                <td>${formatValue(qualityData.speed_cep100)}</td>
                            </tr>
                        `;
                    }
                }
                
                // 处理all定位质量级别
                const allData = devData["all"];
                if (allData) {
                    const allRatio = totalPoints > 0 ? (allData.points / totalPoints * 100).toFixed(1) + "%" : "0%";
                    html += `
                        <tr class="${colorClass}" data-quality="all">
                            <td><strong>${scene.name}</strong></td>
                            <td>${dev}</td>
                            <td>all</td>
                            <td>${allData.points}</td>
                            <td>${allRatio}</td>
                            <td>${formatValue(allData.horz_cep50)}</td>
                            <td>${formatValue(allData.horz_cep68)}</td>
                            <td>${formatValue(allData.horz_cep95)}</td>
                            <td>${formatValue(allData.horz_cep99)}</td>
                            <td>${formatValue(allData.horz_cep100)}</td>
                            <td>${formatValue(allData.vert_cep50)}</td>
                            <td>${formatValue(allData.vert_cep68)}</td>
                            <td>${formatValue(allData.vert_cep95)}</td>
                            <td>${formatValue(allData.vert_cep99)}</td>
                            <td>${formatValue(allData.vert_cep100)}</td>
                            <td>${formatValue(allData.speed_cep50)}</td>
                            <td>${formatValue(allData.speed_cep68)}</td>
                            <td>${formatValue(allData.speed_cep95)}</td>
                            <td>${formatValue(allData.speed_cep99)}</td>
                            <td>${formatValue(allData.speed_cep100)}</td>
                        </tr>
                    `;
                }
            }
        }
    }
    
    html += `</tbody></table></div></div>`;
    
    // 图表与轨迹
    html += ``;
    
    // CEP 柱状图表格 - 按定位质量分行，按CEP类型和级别分列
    const dims = ["horz", "vert", "speed"];
    const dimNames = { "horz": "水平", "vert": "高程", "speed": "速度" };
    const levels = ["50", "68", "95", "99", "100"];
    const qualities = ["0", "1", "2", "4", "5", "6", "all"];

    html += `<div class="card">
        <div class="card-title">
            <h3 id="section-scene-${scene.id}-bar" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">CEP 精度柱状图</h3>
        </div>
        <div class="quality-filters" style="display: none;">
            <label>定位质量筛选：</label>
            <label><input type="checkbox" class="quality-checkbox" value="0"> 0</label>
            <label><input type="checkbox" class="quality-checkbox" value="1"> 1</label>
            <label><input type="checkbox" class="quality-checkbox" value="2"> 2</label>
            <label><input type="checkbox" class="quality-checkbox" value="4"> 4</label>
            <label><input type="checkbox" class="quality-checkbox" value="5"> 5</label>
            <label><input type="checkbox" class="quality-checkbox" value="6"> 6</label>
            <label><input type="checkbox" class="quality-checkbox" value="all" checked> all</label>
        </div>`;

    // 为每个维度创建一个表格
    dims.forEach(dim => {
        html += `
            <div class="table-responsive">
            <table class="cep-chart-table" style="margin-bottom: 0;">
                <thead>
                    <tr>
                        <th style="min-width: 80px;">定位质量</th>
                        ${levels.map(level => `<th>${dimNames[dim]} CEP${level}</th>`).join('')}
                    </tr>
                </thead>
                <tbody>
                    ${qualities.map(q => `
                        <tr data-quality="${q}">
                            <td><strong>${q}</strong></td>
                            ${levels.map(level => `
                                <td>
                                    <div class="chart-item">
                                        <img src="images/${scene.id}_${dim}_cep${level}_bar.png" 
                                             alt="${dimNames[dim]} CEP${level}" 
                                             onerror="this.parentNode.innerHTML='<span style=\'color:#ccc; font-size:1.5rem;\'>-</span>'; this.style.display='none';">
                                    </div>
                                </td>
                            `).join('')}
                        </tr>
                    `).join('')}
                </tbody>
            </table>
            </div>
        `;
    });

    html += `</div>`;

    // 误差图
    html += ``;
    // 分组设备，每组6个
    const deviceChunks = [];
    for (let i = 0; i < config.devices.length; i += 6) {
        deviceChunks.push(config.devices.slice(i, i + 6));
    }

    html += `
        <div class="card">
            <div class="card-title">
                <h3 id="section-scene-${scene.id}-error" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">误差图</h3>
            </div>
            <div style="overflow-x: auto;">
                <table class="error-chart-table" style="width: 100%; table-layout: fixed;">
                    <tbody>
                        ${deviceChunks.map(chunk => `
                            <tr>
                                ${chunk.map(dev => `
                                    <th style="text-align: center; padding: 5px; width: ${100/6}%;">${dev}</th>
                                `).join('')}
                                ${/* 补全空单元格以保持对齐 */ Array(6 - chunk.length).fill('<th style="width: 16.66%;"></th>').join('')}
                            </tr>
                            <tr>
                                ${chunk.map(dev => `
                                    <td style="padding: 5px; vertical-align: top;">
                                        <div class="chart-item" style="border:none; margin: 0;">
                                            <img src="images/${scene.id}_${dev}_error_curve.png" alt="${dev} Error Curve" style="width: 100%; height: auto; display: block;" onerror="this.parentNode.innerHTML='<span style=\'color:#ccc; font-size:1.5rem; display:block; text-align:center; padding:20px;\'>-</span>'; this.style.display='none';">
                                        </div>
                                    </td>
                                `).join('')}
                                ${/* 补全空单元格 */ Array(6 - chunk.length).fill('<td></td>').join('')}
                            </tr>
                        `).join('')}
                    </tbody>
                </table>
            </div>
        </div>
    `;
    
    // 轨迹
    html += `
        <div class="card">
            <div class="card-title">
                <h3 id="section-scene-${scene.id}-track" style="margin: 0; padding: 0; border: none; background: none; font-size: inherit;">轨迹回放</h3>
            </div>
            <iframe src="tracks/${scene.id}_trajectory.html" class="trajectory-frame"></iframe>
        </div>
    `;
    
    section.innerHTML = html;
    return section;
}



function renderLeaderboard() {
    // 功能已删除
}

function initScrollSpy() {
    const navLinks = document.querySelectorAll('#nav-list a');
    // 监听 section 和所有带有 ID 的 h3 (对应子菜单)
    const targets = document.querySelectorAll('section, h3[id^="section-scene-"]');
    
    window.addEventListener('scroll', () => {
        let current = '';
        
        // 查找当前视口中的目标
        targets.forEach(target => {
            const targetTop = target.offsetTop;
            const targetHeight = target.offsetHeight;
            // 调整偏移量以适应视觉位置
            // 只要目标进入视口顶部以下一定距离，就认为激活
            // 并且要确保没有滚过头（对于section来说）
            if (scrollY >= targetTop - 120) {
                current = target.getAttribute('id');
            }
        });
        
        // 如果没有找到当前section（比如滚动到底部空白区），保持最后一个
        // 或者如果滚动到顶部，可能current为空
        
        navLinks.forEach(link => {
            link.classList.remove('active');
            // 移除所有父级li的active类，确保非活动区域自动折叠
            const parentLi = link.closest('li');
            if (parentLi) {
                parentLi.classList.remove('active');
            }
        });

        // 重新激活当前链接及其父级
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (current && href === `#${current}`) {
                link.classList.add('active');
                
                // 找到父级 li 并添加 active 类
                // 如果是子菜单项，需要激活其父级 li 以展开菜单
                const subNav = link.closest('.sub-nav');
                if (subNav) {
                    const parentLi = subNav.parentElement;
                    if (parentLi) parentLi.classList.add('active');
                } else {
                    // 顶级菜单项
                    const parentLi = link.closest('li');
                    if (parentLi && parentLi.parentElement.id === 'nav-list') {
                        parentLi.classList.add('active');
                    }
                }
            }
        });
    });
}

// 切换 CN0 显示模式 (Mean / Max)
window.updateCn0Mode = function(sceneId, mode) {
    const table = document.getElementById(`cn0-table-${sceneId}`);
    if (!table) return;

    // 更新表头标签
    const label = table.querySelector('.cn0-mode-label');
    if (label) {
        label.textContent = mode === 'mean' ? '(Mean)' : '(Max)';
    }

    // 更新所有单元格
    const cells = table.querySelectorAll('.cn0-cell');
    cells.forEach(cell => {
        // 如果是空数据 (-) 则跳过
        if (cell.textContent === '-') return;
        
        const val = cell.getAttribute(`data-${mode}`);
        if (val) {
            cell.textContent = val;
        }
    });
};
