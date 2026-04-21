(function () {
  var CSS = `
    nav.site-nav {
      background: #1a1a1a;
      padding: 12px 32px;
      display: grid;
      grid-template-columns: 1fr auto 1fr;
      align-items: center;
      gap: 16px;
      position: relative;
    }
    nav.site-nav .brand {
      font-family: 'Syne', sans-serif;
      color: #f0e040;
      font-size: 22px;
      text-decoration: none;
      letter-spacing: 1px;
      justify-self: start;
    }
    nav.site-nav .primary {
      display: flex;
      gap: 28px;
      justify-self: center;
    }
    nav.site-nav .primary a {
      color: #ccc;
      text-decoration: none;
      font-size: 14px;
      padding: 6px 2px;
      border-bottom: 2px solid transparent;
      transition: color 0.15s, border-color 0.15s;
    }
    nav.site-nav .primary a:hover { color: white; }
    nav.site-nav .primary a.active {
      color: #f0e040;
      border-bottom-color: #f0e040;
    }
    nav.site-nav .right {
      display: flex;
      align-items: center;
      gap: 14px;
      justify-self: end;
    }
    nav.site-nav .cart-link {
      color: #ccc;
      text-decoration: none;
      font-size: 14px;
      position: relative;
    }
    nav.site-nav .cart-link:hover { color: white; }
    nav.site-nav .cart-badge {
      display: none;
      background: #f0e040;
      color: #1a1a1a;
      font-size: 10px;
      font-weight: 700;
      padding: 1px 6px;
      border-radius: 8px;
      margin-left: 4px;
      vertical-align: top;
    }
    nav.site-nav .login-btn {
      color: #1a1a1a;
      background: #f0e040;
      padding: 6px 14px;
      border-radius: 4px;
      text-decoration: none;
      font-size: 13px;
      font-weight: 600;
    }
    nav.site-nav .login-btn:hover { background: #e0d030; }
    nav.site-nav .account {
      position: relative;
    }
    nav.site-nav .account-btn {
      color: #ccc;
      background: transparent;
      border: 1px solid #444;
      padding: 6px 12px;
      border-radius: 4px;
      font-size: 13px;
      font-family: 'DM Sans', sans-serif;
      cursor: pointer;
    }
    nav.site-nav .account-btn:hover { color: white; border-color: #777; }
    nav.site-nav .account-menu {
      display: none;
      position: absolute;
      right: 0;
      top: calc(100% + 6px);
      background: white;
      border: 1px solid #e0e0e0;
      border-radius: 6px;
      min-width: 200px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.12);
      z-index: 200;
      padding: 6px 0;
    }
    nav.site-nav .account.open .account-menu { display: block; }
    nav.site-nav .account-menu a, nav.site-nav .account-menu button {
      display: block;
      width: 100%;
      text-align: left;
      padding: 9px 16px;
      color: #1a1a1a;
      text-decoration: none;
      font-size: 13px;
      background: none;
      border: none;
      font-family: 'DM Sans', sans-serif;
      cursor: pointer;
    }
    nav.site-nav .account-menu a:hover, nav.site-nav .account-menu button:hover {
      background: #fafaf8;
    }
    nav.site-nav .account-menu .divider {
      height: 1px;
      background: #f0f0f0;
      margin: 4px 0;
    }
    nav.site-nav .account-menu .user-head {
      padding: 10px 16px 6px;
      font-size: 11px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      color: #888;
    }
    nav.site-nav .menu-badge {
      background: #f0e040;
      color: #1a1a1a;
      font-size: 10px;
      font-weight: 700;
      padding: 1px 7px;
      border-radius: 10px;
      margin-left: 6px;
      display: none;
    }
    nav.site-nav .menu-badge.visible { display: inline-block; }
    nav.site-nav .account-menu a { display: flex; justify-content: space-between; align-items: center; }
    nav.site-nav .alert-dot {
      position: absolute;
      top: -3px;
      right: -3px;
      width: 9px;
      height: 9px;
      background: #c62828;
      border-radius: 50%;
      border: 2px solid #1a1a1a;
      display: none;
    }
    nav.site-nav .alert-dot.visible { display: block; }
    nav.site-nav .account-btn { position: relative; }
  `;

  function injectCSS() {
    var style = document.createElement('style');
    style.textContent = CSS;
    document.head.appendChild(style);
  }

  function currentPath() {
    return window.location.pathname;
  }

  function isActive(href) {
    var p = currentPath();
    return p === href || p.endsWith(href);
  }

  function getUserSafe() {
    try {
      var raw = localStorage.getItem('user');
      return raw ? JSON.parse(raw) : null;
    } catch (e) { return null; }
  }

  function loggedIn() {
    return !!localStorage.getItem('token');
  }

  function build() {
    var user = getUserSafe();
    var isAdmin = user && user.role === 'admin';

    var primary = [
      { href: '/pages/buyer/browse.html',    label: 'Browse' },
      { href: '/pages/buyer/auctions.html',  label: 'Auctions' },
      { href: '/pages/seller/dashboard.html', label: 'Sell' }
    ];

    var primaryHtml = primary.map(function (item) {
      var active = isActive(item.href) ? ' class="active"' : '';
      return '<a href="' + item.href + '"' + active + '>' + item.label + '</a>';
    }).join('');

    var rightHtml = '';
    if (loggedIn()) {
      rightHtml += '<a class="cart-link" href="/pages/buyer/cart.html">Cart <span class="cart-badge"></span></a>';
      rightHtml += '<div class="account">';
      rightHtml += '<button type="button" class="account-btn" onclick="window.__toggleAccountMenu(event)">'
                 + (user && user.username ? user.username : 'Account') + ' &#9662;'
                 + '<span class="alert-dot" data-alert-dot></span>'
                 + '</button>';
      rightHtml += '<div class="account-menu">';
      rightHtml += '<div class="user-head">Signed in' + (user && user.username ? ' as ' + user.username : '') + '</div>';
      rightHtml += '<a href="/pages/profile.html"><span>Profile</span></a>';
      rightHtml += '<a href="/pages/seller/dashboard.html"><span>My Listings</span></a>';
      rightHtml += '<a href="/pages/offers/offers.html"><span>Offers</span><span class="menu-badge" data-badge="offers_pending"></span></a>';
      rightHtml += '<a href="/pages/buyer/wishlist.html"><span>Wishlist</span></a>';
      rightHtml += '<a href="/pages/buyer/purchases.html"><span>Purchases</span></a>';
      rightHtml += '<a href="/pages/seller/sales.html"><span>Sales</span></a>';
      if (isAdmin) {
        rightHtml += '<div class="divider"></div>';
        rightHtml += '<a href="/pages/admin/dashboard.html"><span>Admin Dashboard</span><span class="menu-badge" data-badge="admin_pending"></span></a>';
      }
      rightHtml += '<div class="divider"></div>';
      rightHtml += '<button type="button" onclick="window.__navLogout()">Log out</button>';
      rightHtml += '</div></div>';
    } else {
      rightHtml += '<a class="login-btn" href="/pages/auth/login.html">Login</a>';
    }

    return (
      '<nav class="site-nav">' +
        '<a class="brand" href="/pages/buyer/browse.html">Switchr</a>' +
        '<div class="primary">' + primaryHtml + '</div>' +
        '<div class="right">' + rightHtml + '</div>' +
      '</nav>'
    );
  }

  window.__toggleAccountMenu = function (e) {
    e.stopPropagation();
    var parent = e.currentTarget.parentElement;
    parent.classList.toggle('open');
  };

  window.__navLogout = function () {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
    window.location.href = '/pages/auth/login.html';
  };

  document.addEventListener('click', function (e) {
    var open = document.querySelector('nav.site-nav .account.open');
    if (open && !open.contains(e.target)) open.classList.remove('open');
  });

  function updateCartBadge() {
    if (!loggedIn()) return;
    fetch('/api/cart', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    })
    .then(function (r) { return r.json(); })
    .then(function (d) {
      var count = (d.cart || []).length;
      var badge = document.querySelector('nav.site-nav .cart-badge');
      if (!badge) return;
      if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
      } else {
        badge.style.display = 'none';
      }
    })
    .catch(function () {});
  }

  function updateNavCounts() {
    if (!loggedIn()) return;
    fetch('/api/nav-counts', {
      headers: { 'Authorization': 'Bearer ' + localStorage.getItem('token') }
    })
    .then(function (r) { return r.ok ? r.json() : null; })
    .then(function (d) {
      if (!d) return;
      var total = 0;
      document.querySelectorAll('nav.site-nav .menu-badge').forEach(function (el) {
        var key = el.getAttribute('data-badge');
        var n = d[key] || 0;
        total += n;
        if (n > 0) {
          el.textContent = n;
          el.classList.add('visible');
        } else {
          el.classList.remove('visible');
        }
      });
      var dot = document.querySelector('nav.site-nav [data-alert-dot]');
      if (dot) dot.classList.toggle('visible', total > 0);
    })
    .catch(function () {});
  }

  function ensureAuthLinksStub() {
    if (document.getElementById('authLinks')) return;
    var stub = document.createElement('span');
    stub.id = 'authLinks';
    stub.style.display = 'none';
    (document.body || document.documentElement).appendChild(stub);
  }

  function mount() {
    var root = document.getElementById('nav-root');
    if (!root) return;
    injectCSS();
    root.outerHTML = build();
    ensureAuthLinksStub();
    updateCartBadge();
    updateNavCounts();
    setInterval(updateNavCounts, 30000);
  }

  // Mount eagerly: the <script> tag always follows <div id="nav-root">,
  // so the target already exists and we should run before any inline page JS
  // that references now-removed nav elements (e.g. #authLinks).
  mount();
})();
