const pb = new PocketBase('http://localhost:8090');

// Load auth dari localStorage ke SDK
const savedToken = localStorage.getItem('pb_token');
const savedUser = localStorage.getItem('pb_user');
if (savedToken && savedUser) {
    pb.authStore.save(savedToken, JSON.parse(savedUser));
}

// Utilitas global
function showToast(message, type = 'info') {
    // type: 'success' | 'error' | 'info'
    const toast = document.createElement('div');
    toast.className = 'fixed top-4 left-1/2 -translate-x-1/2 px-4 py-2 rounded shadow-lg z-[9999] transition-all duration-300 text-white';
    
    if (type === 'success') toast.classList.add('bg-green-500');
    else if (type === 'error') toast.classList.add('bg-red-500');
    else toast.classList.add('bg-blue-500');
    
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleDateString('id-ID', {
        day: '2-digit', month: 'short', year: 'numeric'
    }) + ', ' + d.toLocaleTimeString('id-ID', {
        hour: '2-digit', minute: '2-digit'
    });
}

function getInitials(name) {
    if (!name) return '??';
    return name.trim().substring(0, 2).toUpperCase();
}

function getAvatarColor(name) {
    const colors = ['#6366f1','#0ea5e9','#8b5cf6','#f59e0b','#14b8a6'];
    const idx = (name || '').split('')
        .reduce((a, c) => a + c.charCodeAt(0), 0);
    return colors[idx % colors.length];
}

function logout() {
    pb.collection('submissions').unsubscribe('*');
    pb.authStore.clear();
    localStorage.removeItem('pb_token');
    localStorage.removeItem('pb_user');
    localStorage.removeItem('last_submit_time');
    window.location.href = '/index.html';
}
