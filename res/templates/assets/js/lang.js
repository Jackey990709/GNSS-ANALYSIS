/**
 * 共享中英文切换脚本
 * 供 data/ 目录下各报告页使用，语言状态与 index.html 共用 localStorage('gnss-lang')。
 * 各页面翻译字典集中维护在下方 window.LANG_KEYS，元素加 data-i18n 属性标记待翻译文本。
 */
window.LANG_KEYS = {
    // index.html 导航翻译（以 index 短标签为准，覆盖上方同名键）
    'GNSS Report': { en: 'GNSS Report', zh: 'GNSS 报告' },
    'Report': { en: 'Report', zh: '报告' },
    'Satellites Trend': { en: 'Satellites Trend', zh: 'GGA 卫星数' },
    'SVs Used Trend': { en: 'SVs Used Trend', zh: 'GSA 卫星数' },
    'CN0 Trend': { en: 'CN0 Trend', zh: 'CN0 趋势' },
    'GPS CN0': { en: 'GPS CN0', zh: 'GPS CN0' },
    'BDS1 CN0': { en: 'BDS1 CN0', zh: 'BDS1 CN0' },
    'BDS2 CN0': { en: 'BDS2 CN0', zh: 'BDS2 CN0' },
    'GAL CN0': { en: 'GAL CN0', zh: 'GAL CN0' },
    'GLO CN0': { en: 'GLO CN0', zh: 'GLO CN0' },
    'QZSS CN0': { en: 'QZSS CN0', zh: 'QZSS CN0' },
    'IRNSS CN0': { en: 'IRNSS CN0', zh: 'IRNSS CN0' },
    'SOG Trend': { en: 'SOG Trend', zh: '对地速度' },
    'COG Trend': { en: 'COG Trend', zh: '对地航向' },
    'DOP Trend': { en: 'DOP Trend', zh: 'DOP 趋势' },
    'Alt/Sep Trend': { en: 'Alt/Sep Trend', zh: '海拔高/分离度' },
    'Accuracy Trend': { en: 'Accuracy Trend', zh: '所有解精度' },
    'Time Continuity': { en: 'Time Continuity', zh: '时间连续性' },
    'Fix Accuracy Trend': { en: 'Fix Accuracy Trend', zh: '固定解精度' },
    'Float Accuracy Trend': { en: 'Float Accuracy Trend', zh: '浮点解精度' },
    'PQTMVEL Trend': { en: 'PQTMVEL Trend', zh: 'PQTMVEL' },
    'RTK Delay': { en: 'RTK Delay', zh: 'RTK 延迟' },
    // 趋势页说明文字（键 = 文件名）
    'accuracy_trend': { en: 'Statistics of horizontal/vertical errors for all solutions', zh: '统计所有解水平/高程误差' },
    'svs_used_trend': { en: 'Statistics of satellite number in GSA', zh: '统计GSA中卫星个数' },
    'gps_cn0': { en: 'Statistics of GPS CN0 in GSV', zh: '统计GSV中GPS卫星信噪比' },
    'bds1_cn0': { en: 'Statistics of BDS(B1I+B2a+B2b) CN0 in GSV', zh: '统计GSV中BDS(B1I+B2a+B2b)卫星信噪比' },
    'bds2_cn0': { en: 'Statistics of BDS(B1C+B2I+B3I) CN0 in GSV', zh: '统计GSV中BDS(B1C+B2I+B3I)卫星信噪比' },
    'gal_cn0': { en: 'Statistics of GAL CN0 in GSV', zh: '统计GSV中GAL卫星信噪比' },
    'glo_cn0': { en: 'Statistics of GLO CN0 in GSV', zh: '统计GSV中GLO卫星信噪比' },
    'qzss_cn0': { en: 'Statistics of QZSS CN0 in GSV', zh: '统计GSV中QZSS卫星信噪比' },
    'irnss_cn0': { en: 'Statistics of IRNSS CN0 in GSV', zh: '统计GSV中IRNSS卫星信噪比' },
    'msl_alt/geo_sep_trend': { en: 'Statistics of altitude and geoid separation in GGA', zh: '统计GGA中高度和大地水准面分离变化' },
    'cog_trend': { en: 'Statistics of heading angle changes in RMC', zh: '统计RMC中航向角变化' },
    'dop_trend': { en: 'Statistics of DOP values in GSA sentences', zh: '统计GSA语句中DOP值' },
    'fix_accuracy_trend': { en: 'Statistics of horizontal/vertical errors for fixed solutions', zh: '统计固定解水平/高程误差' },
    'float_accuracy_trend': { en: 'Statistics of horizontal/vertical errors for float solutions', zh: '统计浮点解水平/高程误差' },
    'rtk_delay': { en: 'Statistics of RTK delay in GGA', zh: '统计GGA中RTK时延' },
    'satellites_trend': { en: 'Statistics of satellite count in GGA', zh: '统计GGA中卫星个数' },
    'sog_trend': { en: 'Statistics of speed error in RMC', zh: '统计RMC中速度误差' },
    'time_continuity': { en: 'Statistics of RMC time continuity in milliseconds', zh: '统计RMC时间连续性，单位为ms' },
    // 精度图表 series 名
    'Positional Accuracy': { en: 'Positional Accuracy', zh: '位置精度' },
    'Altitude Accuracy': { en: 'Altitude Accuracy', zh: '高程精度' },
    // COG/SOG series 名
    'COG Accuracy': { en: 'COG Accuracy', zh: '对地航向' },
    'SOG Accuracy': { en: 'SOG Accuracy', zh: '对地速度' },
    // Alt/Sep series 名
    'MSL Alt': { en: 'MSL Alt', zh: '海拔高' },
    'GEO Sep': { en: 'GEO Sep', zh: '分离度' },
    // time_continuity 名
    'Millisecond': { en: 'Millisecond', zh: '毫秒' },
    'Quality': { en: 'Quality', zh: '定位符' },
    // rtk delay 名
    'delay': { en: 'delay', zh: '时延' }
};

(function () {
    var STORAGE_KEY = 'gnss-lang';

    function currentLang() {
        try {
            return localStorage.getItem(STORAGE_KEY) === 'zh' ? 'zh' : 'en';
        } catch (e) {
            return 'en';
        }
    }

    function t(key) {
        var map = window.LANG_KEYS || {};
        var entry = map[key];
        if (!entry) return key;
        var lang = currentLang();
        return entry[lang] !== undefined ? entry[lang] : entry.en !== undefined ? entry.en : key;
    }

    function applyLang() {
        // 更新 document.title
        var titleKey = document.body.getAttribute('data-i18n-title');
        if (titleKey) {
            document.title = t(titleKey);
        }
        // 更新带 data-i18n 属性的元素
        var nodes = document.querySelectorAll('[data-i18n]');
        for (var i = 0; i < nodes.length; i++) {
            var node = nodes[i];
            var key = node.getAttribute('data-i18n');
            var val = t(key);
            if (node.tagName === 'TITLE') {
                node.textContent = val;
            } else {
                node.textContent = val;
            }
        }
        // 触发页面级回调（如需处理动态内容）
        if (window.onLangChange) {
            window.onLangChange(t);
        }
    }

    function initLang() {
        applyLang();
        // 监听同源其他页面（index.html）的语言变更
        if (window.addEventListener) {
            window.addEventListener('storage', function (e) {
                if (e.key === STORAGE_KEY || e.key === null) {
                    applyLang();
                }
            });
        }
    }

    window.initLang = initLang;
    window.t = t;
    window.currentLang = currentLang;
})();
