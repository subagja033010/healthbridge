import { useState, useEffect } from "react";
import axios from "axios";
import "./index.css";

const API_URL = "http://127.0.0.1:8000";

// Generate session ID untuk keranjang
const getSessionId = () => {
  let sessionId = localStorage.getItem("healthbridge_session");
  if (!sessionId) {
    sessionId = "session_" + Date.now() + "_" + Math.random().toString(36).substr(2, 9);
    localStorage.setItem("healthbridge_session", sessionId);
  }
  return sessionId;
};

// Get auth token
const getAuthToken = () => localStorage.getItem("healthbridge_token");
const setAuthToken = (token) => localStorage.setItem("healthbridge_token", token);
const removeAuthToken = () => localStorage.removeItem("healthbridge_token");

// Get user from localStorage
const getSavedUser = () => {
  const user = localStorage.getItem("healthbridge_user");
  return user ? JSON.parse(user) : null;
};
const setSavedUser = (user) => localStorage.setItem("healthbridge_user", JSON.stringify(user));
const removeSavedUser = () => localStorage.removeItem("healthbridge_user");

// Emoji icons untuk setiap penyakit
const diseaseIcons = {
  "Demam": "🤒",
  "Flu (Influenza)": "🤧",
  "Maag (Gastritis)": "🤢",
  "Migrain": "🤕",
  "Dermatitis Alergi": "😷",
  "Hipertensi": "❤️‍🔥",
  "Diabetes Mellitus": "🩸",
  "Vertigo": "😵‍💫",
  "Asma": "😮‍💨",
  "Tifus (Demam Tifoid)": "🤮",
  "Sakit Gigi": "🦷",
  "Diare": "🚽",
  "Sariawan": "👄",
  "Sakit Mata (Konjungtivitis)": "👁️",
  "Sakit Telinga (Otitis)": "👂"
};

const categoryColors = {
  "Infeksi": "#e74c3c",
  "Infeksi Virus": "#e74c3c",
  "Infeksi Bakteri": "#c0392b",
  "Pencernaan": "#f39c12",
  "Neurologis": "#9b59b6",
  "Kulit": "#1abc9c",
  "Kardiovaskular": "#e91e63",
  "Metabolik": "#3498db",
  "Pernapasan": "#00bcd4",
  "Gigi & Mulut": "#ff6b6b",
  "Mata": "#2ecc71",
  "THT": "#8e44ad",
  // Kategori obat
  "Analgesik": "#e74c3c",
  "Anti-inflamasi": "#c0392b",
  "Flu": "#3498db",
  "Batuk": "#9b59b6",
  "Alergi": "#f39c12",
  "Vitamin": "#2ecc71",
  "Otot": "#e91e63",
  "Mulut": "#ff6b6b"
};

// Format harga Rupiah
const formatRupiah = (number) => {
  return new Intl.NumberFormat('id-ID', {
    style: 'currency',
    currency: 'IDR',
    minimumFractionDigits: 0
  }).format(number);
};

function App() {
  // State untuk navigasi
  const [currentPage, setCurrentPage] = useState("landing");
  const [sessionId] = useState(getSessionId());

  // Auth state
  const [user, setUser] = useState(getSavedUser());
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");

  // Login form
  const [loginEmail, setLoginEmail] = useState("");
  const [loginPassword, setLoginPassword] = useState("");

  // Register form
  const [registerName, setRegisterName] = useState("");
  const [registerEmail, setRegisterEmail] = useState("");
  const [registerPassword, setRegisterPassword] = useState("");
  const [registerConfirm, setRegisterConfirm] = useState("");

  // State untuk konsultasi
  const [name, setName] = useState("");
  const [symptoms, setSymptoms] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  // State untuk katalog penyakit
  const [diseases, setDiseases] = useState([]);
  const [selectedDisease, setSelectedDisease] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");

  // State untuk toko obat
  const [medicines, setMedicines] = useState([]);
  const [medicineSearch, setMedicineSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("Semua");

  // State untuk keranjang
  const [cart, setCart] = useState({ items: [], total_items: 0, total_price: 0 });
  const [showCart, setShowCart] = useState(false);
  const [cartLoading, setCartLoading] = useState(false);

  // State untuk checkout
  const [showCheckout, setShowCheckout] = useState(false);
  const [checkoutData, setCheckoutData] = useState({ customer_name: "", phone: "", address: "" });
  const [orderSuccess, setOrderSuccess] = useState(null);

  // State untuk detail obat modal
  const [selectedMedicine, setSelectedMedicine] = useState(null);

  // State untuk riwayat pesanan user
  const [userOrders, setUserOrders] = useState([]);
  const [orderSearchPhone, setOrderSearchPhone] = useState("");
  const [ordersLoading, setOrdersLoading] = useState(false);

  // Admin state
  const [adminStats, setAdminStats] = useState(null);
  const [adminOrders, setAdminOrders] = useState([]);
  const [adminUsers, setAdminUsers] = useState([]);
  const [adminTab, setAdminTab] = useState("dashboard");

  // Admin medicine form
  const [showAddMedicine, setShowAddMedicine] = useState(false);
  const [editMedicine, setEditMedicine] = useState(null);
  const [medicineForm, setMedicineForm] = useState({
    name: "", description: "", category: "", price: 0, stock: 100, image_url: ""
  });
  const [imageUploading, setImageUploading] = useState(false);
  const [availableImages, setAvailableImages] = useState([]);
  const [showImageGallery, setShowImageGallery] = useState(false);

  // Auth headers helper
  const getAuthHeaders = () => ({
    headers: { Authorization: `Bearer ${getAuthToken()}` }
  });

  // Handle login
  const handleLogin = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");

    try {
      const response = await axios.post(`${API_URL}/api/auth/login`, {
        email: loginEmail,
        password: loginPassword
      });

      const { access_token, user: userData } = response.data;
      setAuthToken(access_token);
      setSavedUser(userData);
      setUser(userData);
      setLoginEmail("");
      setLoginPassword("");

      // Redirect based on role
      if (userData.role === "admin") {
        setCurrentPage("admin");
      } else {
        setCurrentPage("landing");
      }
    } catch (error) {
      setAuthError(error.response?.data?.detail || "Login gagal");
    } finally {
      setAuthLoading(false);
    }
  };

  // Handle register
  const handleRegister = async (e) => {
    e.preventDefault();
    setAuthLoading(true);
    setAuthError("");

    if (registerPassword !== registerConfirm) {
      setAuthError("Password tidak cocok");
      setAuthLoading(false);
      return;
    }

    try {
      await axios.post(`${API_URL}/api/auth/register`, {
        email: registerEmail,
        password: registerPassword,
        name: registerName
      });

      alert("Registrasi berhasil! Silakan login.");
      setCurrentPage("login");
      setRegisterName("");
      setRegisterEmail("");
      setRegisterPassword("");
      setRegisterConfirm("");
    } catch (error) {
      setAuthError(error.response?.data?.detail || "Registrasi gagal");
    } finally {
      setAuthLoading(false);
    }
  };

  // Handle diagnose
  const handleDiagnose = async () => {
    if (!name || !symptoms) {
      alert("Harap isi nama dan keluhan Anda");
      return;
    }

    setLoading(true);
    setResult(null);

    try {
      const response = await axios.post(`${API_URL}/api/diagnose`, {
        patient_name: name,
        symptoms: symptoms
      });

      console.log("Diagnose result:", response.data);
      setResult(response.data);
    } catch (error) {
      console.error("Error diagnosing:", error);
      alert("Maaf, terjadi kesalahan saat menganalisa. Silakan coba lagi.");
    } finally {
      setLoading(false);
    }
  };

  // Handle logout
  const handleLogout = () => {
    removeAuthToken();
    removeSavedUser();
    setUser(null);
    setCurrentPage("landing");
  };

  // Fetch admin data
  const fetchAdminDashboard = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/dashboard`, getAuthHeaders());
      setAdminStats(response.data.stats);
    } catch (error) {
      console.error("Error fetching admin dashboard:", error);
      if (error.response?.status === 401 || error.response?.status === 403) {
        handleLogout();
      }
    }
  };

  const fetchAdminOrders = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/orders`, getAuthHeaders());
      setAdminOrders(response.data);
    } catch (error) {
      console.error("Error fetching admin orders:", error);
    }
  };

  const fetchAdminUsers = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/admin/users`, getAuthHeaders());
      setAdminUsers(response.data);
    } catch (error) {
      console.error("Error fetching admin users:", error);
    }
  };

  const updateOrderStatus = async (orderId, newStatus) => {
    try {
      await axios.put(`${API_URL}/api/admin/orders/${orderId}`, { status: newStatus }, getAuthHeaders());
      fetchAdminOrders();
    } catch (error) {
      console.error("Error updating order:", error);
    }
  };

  // Admin medicine CRUD
  const handleSaveMedicine = async () => {
    try {
      if (editMedicine) {
        await axios.put(`${API_URL}/api/admin/medicines/${editMedicine.id}`, medicineForm, getAuthHeaders());
      } else {
        await axios.post(`${API_URL}/api/admin/medicines`, medicineForm, getAuthHeaders());
      }
      setShowAddMedicine(false);
      setEditMedicine(null);
      setMedicineForm({ name: "", description: "", category: "", price: 0, stock: 100, image_url: "" });
      fetchMedicines();
    } catch (error) {
      alert(error.response?.data?.detail || "Gagal menyimpan obat");
    }
  };

  const handleDeleteMedicine = async (id) => {
    if (!window.confirm("Yakin hapus obat ini?")) return;
    try {
      await axios.delete(`${API_URL}/api/admin/medicines/${id}`, getAuthHeaders());
      fetchMedicines();
    } catch (error) {
      alert("Gagal menghapus obat");
    }
  };

  // Handle image upload
  const handleImageUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    // Validasi ukuran file (max 5MB)
    if (file.size > 5 * 1024 * 1024) {
      alert("Ukuran file maksimal 5MB");
      return;
    }

    setImageUploading(true);
    const formData = new FormData();
    formData.append("file", file);
    // Kirim nama produk untuk auto-rename file
    if (medicineForm.name) {
      formData.append("product_name", medicineForm.name);
    }

    try {
      const response = await axios.post(`${API_URL}/api/upload/image`, formData, {
        headers: { "Content-Type": "multipart/form-data" }
      });

      if (response.data.status === "success") {
        setMedicineForm(prev => ({ ...prev, image_url: response.data.image_url }));
        alert(`✅ Gambar berhasil diupload!\nNama file: ${response.data.filename}`);
      }
    } catch (error) {
      alert(error.response?.data?.detail || "Gagal mengupload gambar");
    } finally {
      setImageUploading(false);
    }
  };

  // Fetch available images from server
  const fetchAvailableImages = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/images`);
      setAvailableImages(response.data.images || []);
    } catch (error) {
      console.error("Error fetching images:", error);
    }
  };

  // Fetch diseases
  useEffect(() => {
    if (currentPage === "catalog" || currentPage === "consult") {
      fetchDiseases();
    }
  }, [currentPage]);

  // Fetch medicines
  useEffect(() => {
    if (currentPage === "store" || (currentPage === "admin" && adminTab === "products")) {
      fetchMedicines();
    }
  }, [currentPage, adminTab]);

  // Fetch cart
  useEffect(() => {
    fetchCart();
  }, [sessionId]);

  // Fetch admin data
  useEffect(() => {
    if (currentPage === "admin" && user?.role === "admin") {
      if (adminTab === "dashboard") fetchAdminDashboard();
      if (adminTab === "orders") fetchAdminOrders();
      if (adminTab === "users") fetchAdminUsers();
      if (adminTab === "products") fetchMedicines();
    }
  }, [currentPage, adminTab, user]);

  const fetchDiseases = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/diseases`);
      setDiseases(response.data);
    } catch (error) {
      console.error("Error fetching diseases:", error);
    }
  };

  const fetchMedicines = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/medicines`);
      setMedicines(response.data);
    } catch (error) {
      console.error("Error fetching medicines:", error);
    }
  };

  const fetchCart = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/cart/${sessionId}`);
      setCart(response.data);
    } catch (error) {
      console.error("Error fetching cart:", error);
    }
  };

  const addToCart = async (medicineId, medicineName) => {
    setCartLoading(true);
    try {
      await axios.post(`${API_URL}/api/cart/add`, {
        session_id: sessionId,
        medicine_id: medicineId,
        quantity: 1
      });
      await fetchCart();
      alert(`✅ ${medicineName} ditambahkan ke keranjang!`);
    } catch (error) {
      console.error("Error adding to cart:", error);
      alert("Gagal menambahkan ke keranjang");
    } finally {
      setCartLoading(false);
    }
  };

  const updateCartItem = async (itemId, newQuantity) => {
    try {
      await axios.put(`${API_URL}/api/cart/update/${itemId}?quantity=${newQuantity}`);
      await fetchCart();
    } catch (error) {
      console.error("Error updating cart:", error);
    }
  };

  const removeFromCart = async (itemId) => {
    try {
      await axios.delete(`${API_URL}/api/cart/remove/${itemId}`);
      await fetchCart();
    } catch (error) {
      console.error("Error removing from cart:", error);
    }
  };

  const handleCheckout = async () => {
    if (!checkoutData.customer_name || !checkoutData.phone || !checkoutData.address) {
      alert("Harap isi semua data!");
      return;
    }

    try {
      const response = await axios.post(`${API_URL}/api/order/checkout`, {
        session_id: sessionId,
        ...checkoutData
      });

      if (response.data.status === "success") {
        setOrderSuccess(response.data.order);
        setShowCheckout(false);
        setShowCart(false);
        setOrderSearchPhone(checkoutData.phone); // Save phone for order tracking
        await fetchCart();
      } else {
        alert(response.data.message);
      }
    } catch (error) {
      console.error("Error checkout:", error);
      alert("Gagal memproses pesanan");
    }
  };

  // Fetch user orders by phone
  const fetchUserOrders = async (phone) => {
    if (!phone) {
      alert("Masukkan nomor telepon!");
      return;
    }
    setOrdersLoading(true);
    try {
      const response = await axios.get(`${API_URL}/api/orders/${phone}`);
      setUserOrders(response.data.orders || []);
    } catch (error) {
      console.error("Error fetching orders:", error);
      setUserOrders([]);
    } finally {
      setOrdersLoading(false);
    }
  };



  const filteredDiseases = diseases.filter(disease =>
    disease.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    disease.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
    disease.symptoms.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Filter medicines
  const categories = ["Semua", ...new Set(medicines.map(m => m.category))];
  const filteredMedicines = medicines.filter(medicine => {
    const matchesSearch = medicine.name.toLowerCase().includes(medicineSearch.toLowerCase()) ||
      medicine.description.toLowerCase().includes(medicineSearch.toLowerCase());
    const matchesCategory = selectedCategory === "Semua" || medicine.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  // --- USER NAV COMPONENT ---
  const UserNav = () => (
    <div className="user-nav">
      <button className="btn-orders-nav" onClick={() => setCurrentPage("orders")}>
        📋 Pesanan
      </button>
      {user ? (
        <>
          <span className="user-welcome">👋 Halo, {user.name}</span>
          {user.role === "admin" && (
            <button className="btn-admin-nav" onClick={() => setCurrentPage("admin")}>
              ⚙️ Admin
            </button>
          )}
          <button className="btn-logout" onClick={handleLogout}>Logout</button>
        </>
      ) : (
        <>
          <button className="btn-login-nav" onClick={() => setCurrentPage("login")}>Masuk</button>
          <button className="btn-register-nav" onClick={() => setCurrentPage("register")}>Daftar</button>
        </>
      )}
    </div>
  );

  // --- FLOATING CART BUTTON ---
  const CartButton = () => (
    <div className="floating-cart" onClick={() => setShowCart(true)}>
      <span className="cart-icon">🛒</span>
      {cart.total_items > 0 && (
        <span className="cart-badge">{cart.total_items}</span>
      )}
    </div>
  );

  // --- CART MODAL ---
  const CartModal = () => (
    <div className="modal-overlay" onClick={() => setShowCart(false)}>
      <div className="cart-modal" onClick={(e) => e.stopPropagation()}>
        <button className="modal-close" onClick={() => setShowCart(false)}>✕</button>
        <h2>🛒 Keranjang Belanja</h2>

        {cart.items.length === 0 ? (
          <div className="empty-cart">
            <span className="empty-icon">🛒</span>
            <p>Keranjang masih kosong</p>
            <button className="btn-shop" onClick={() => { setShowCart(false); setCurrentPage("store"); }}>
              Belanja Sekarang
            </button>
          </div>
        ) : (
          <>
            <div className="cart-items">
              {cart.items.map(item => (
                <div key={item.id} className="cart-item">
                  <div className="cart-item-info">
                    <h4>{item.medicine_name}</h4>
                    <p>{formatRupiah(item.medicine_price)}</p>
                  </div>
                  <div className="cart-item-actions">
                    <button onClick={() => updateCartItem(item.id, Math.max(1, item.quantity - 1))}>-</button>
                    <span>{item.quantity}</span>
                    <button onClick={() => updateCartItem(item.id, item.quantity + 1)}>+</button>
                    <button className="btn-remove" onClick={() => removeFromCart(item.id)}>🗑️</button>
                  </div>
                  <div className="cart-item-subtotal">
                    {formatRupiah(item.subtotal)}
                  </div>
                </div>
              ))}
            </div>
            <div className="cart-total">
              <span>Total:</span>
              <strong>{formatRupiah(cart.total_price)}</strong>
            </div>
            <button className="btn-checkout" onClick={() => setShowCheckout(true)}>
              Checkout Sekarang
            </button>
          </>
        )}
      </div>
    </div>
  );

  // --- CHECKOUT MODAL ---
  const renderCheckoutModal = () => {
    if (!showCheckout) return null;

    return (
      <div className="modal-overlay" onClick={() => setShowCheckout(false)}>
        <div className="checkout-modal" onClick={(e) => e.stopPropagation()}>
          <button className="modal-close" onClick={() => setShowCheckout(false)}>✕</button>
          <h2>📦 Checkout</h2>

          <div className="checkout-form">
            <div className="form-group">
              <label>Nama Lengkap</label>
              <input
                type="text"
                placeholder="Masukkan nama lengkap..."
                value={checkoutData.customer_name}
                onChange={(e) => setCheckoutData(prev => ({ ...prev, customer_name: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label>Nomor Telepon</label>
              <input
                type="tel"
                placeholder="Contoh: 081234567890"
                value={checkoutData.phone}
                onChange={(e) => setCheckoutData(prev => ({ ...prev, phone: e.target.value }))}
                autoComplete="off"
              />
            </div>
            <div className="form-group">
              <label>Alamat Pengiriman</label>
              <textarea
                placeholder="Masukkan alamat lengkap..."
                value={checkoutData.address}
                onChange={(e) => setCheckoutData(prev => ({ ...prev, address: e.target.value }))}
                autoComplete="off"
              />
            </div>
          </div>

          <div className="checkout-summary">
            <h4>Ringkasan Pesanan</h4>
            {cart.items.map(item => (
              <div key={item.id} className="checkout-item">
                <span>{item.medicine_name} x{item.quantity}</span>
                <span>{formatRupiah(item.subtotal)}</span>
              </div>
            ))}
            <div className="checkout-total">
              <strong>Total Bayar:</strong>
              <strong>{formatRupiah(cart.total_price)}</strong>
            </div>
          </div>

          <button className="btn-confirm-order" onClick={handleCheckout}>
            ✅ Konfirmasi Pesanan
          </button>
        </div>
      </div>
    );
  };

  // --- ORDER SUCCESS MODAL ---
  const OrderSuccessModal = () => (
    <div className="modal-overlay" onClick={() => setOrderSuccess(null)}>
      <div className="success-modal" onClick={(e) => e.stopPropagation()}>
        <div className="success-icon">🎉</div>
        <h2>Pesanan Berhasil!</h2>
        <p>Terima kasih, pesanan Anda sedang diproses.</p>

        <div className="order-details">
          <p><strong>No. Pesanan:</strong> #{orderSuccess.id}</p>
          <p><strong>Nama:</strong> {orderSuccess.customer_name}</p>
          <p><strong>Total:</strong> {formatRupiah(orderSuccess.total_price)}</p>
        </div>

        <button className="btn-close-success" onClick={() => setOrderSuccess(null)}>
          Tutup
        </button>
      </div>
    </div>
  );

  // --- LOGIN PAGE ---
  if (currentPage === "login") {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <div className="auth-logo">🔐</div>
          <h1>Masuk ke HealthBridge</h1>
          <p>Silakan masuk untuk melanjutkan</p>

          {authError && <div className="auth-error">{authError}</div>}

          <form onSubmit={handleLogin}>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                placeholder="contoh@email.com"
                value={loginEmail}
                onChange={(e) => setLoginEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Masukkan password"
                value={loginPassword}
                onChange={(e) => setLoginPassword(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-auth-submit" disabled={authLoading}>
              {authLoading ? "⏳ Loading..." : "Masuk"}
            </button>
          </form>

          <div className="auth-footer">
            <p>Belum punya akun? <span onClick={() => setCurrentPage("register")}>Daftar sekarang</span></p>
            <p><span onClick={() => setCurrentPage("landing")}>← Kembali ke beranda</span></p>
          </div>
        </div>
      </div>
    );
  }

  // --- REGISTER PAGE ---
  if (currentPage === "register") {
    return (
      <div className="auth-container">
        <div className="auth-box">
          <div className="auth-logo">📝</div>
          <h1>Daftar Akun Baru</h1>
          <p>Buat akun untuk menggunakan HealthBridge</p>

          {authError && <div className="auth-error">{authError}</div>}

          <form onSubmit={handleRegister}>
            <div className="form-group">
              <label>Nama Lengkap</label>
              <input
                type="text"
                placeholder="Masukkan nama lengkap"
                value={registerName}
                onChange={(e) => setRegisterName(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Email</label>
              <input
                type="email"
                placeholder="contoh@email.com"
                value={registerEmail}
                onChange={(e) => setRegisterEmail(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Password</label>
              <input
                type="password"
                placeholder="Minimal 6 karakter"
                value={registerPassword}
                onChange={(e) => setRegisterPassword(e.target.value)}
                required
              />
            </div>
            <div className="form-group">
              <label>Konfirmasi Password</label>
              <input
                type="password"
                placeholder="Ulangi password"
                value={registerConfirm}
                onChange={(e) => setRegisterConfirm(e.target.value)}
                required
              />
            </div>
            <button type="submit" className="btn-auth-submit" disabled={authLoading}>
              {authLoading ? "⏳ Loading..." : "Daftar"}
            </button>
          </form>

          <div className="auth-footer">
            <p>Sudah punya akun? <span onClick={() => setCurrentPage("login")}>Masuk di sini</span></p>
            <p><span onClick={() => setCurrentPage("landing")}>← Kembali ke beranda</span></p>
          </div>
        </div>
      </div>
    );
  }

  // --- HALAMAN RIWAYAT PESANAN ---
  if (currentPage === "orders") {
    // Helper function for status badge
    const getStatusBadge = (status) => {
      const statusConfig = {
        pending: { label: "Menunggu", color: "#f39c12", icon: "⏳" },
        processing: { label: "Diproses", color: "#3498db", icon: "🔄" },
        shipped: { label: "Dikirim", color: "#9b59b6", icon: "🚚" },
        delivered: { label: "Sampai", color: "#27ae60", icon: "✅" },
        cancelled: { label: "Dibatalkan", color: "#e74c3c", icon: "❌" }
      };
      const config = statusConfig[status?.toLowerCase()] || statusConfig.pending;
      return (
        <span className="order-status-badge" style={{ backgroundColor: config.color }}>
          {config.icon} {config.label}
        </span>
      );
    };

    return (
      <div className="app-container orders-container">
        <UserNav />
        <CartButton />
        <div className="nav-buttons">
          <button className="btn-back" onClick={() => setCurrentPage("landing")}>
            ⬅ Kembali
          </button>
        </div>

        <h1>📋 Riwayat Pesanan</h1>
        <p className="subtitle">Lacak status pesanan Anda dengan memasukkan nomor telepon</p>

        <div className="order-search-box">
          <div className="order-search-form">
            <input
              type="tel"
              placeholder="Masukkan nomor telepon (contoh: 081234567890)"
              value={orderSearchPhone}
              onChange={(e) => setOrderSearchPhone(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && fetchUserOrders(orderSearchPhone)}
            />
            <button
              className="btn-search-order"
              onClick={() => fetchUserOrders(orderSearchPhone)}
              disabled={ordersLoading}
            >
              {ordersLoading ? "⏳ Mencari..." : "🔍 Cari Pesanan"}
            </button>
          </div>
        </div>

        <div className="orders-list">
          {userOrders.length === 0 ? (
            <div className="empty-orders">
              <span className="empty-icon">📦</span>
              <p>Belum ada pesanan ditemukan</p>
              <p className="empty-hint">Masukkan nomor telepon yang digunakan saat checkout</p>
            </div>
          ) : (
            userOrders.map(order => (
              <div key={order.id} className="order-card">
                <div className="order-header">
                  <div className="order-id">
                    <span className="order-number">Pesanan #{order.id}</span>
                    <span className="order-date">{order.created_at}</span>
                  </div>
                  {getStatusBadge(order.status)}
                </div>

                <div className="order-items">
                  {order.items.map((item, idx) => (
                    <div key={idx} className="order-item-row">
                      <span className="item-name">{item.name}</span>
                      <span className="item-qty">x{item.quantity}</span>
                      <span className="item-price">{formatRupiah(item.subtotal)}</span>
                    </div>
                  ))}
                </div>

                <div className="order-footer">
                  <div className="order-address">
                    <strong>📍 Alamat:</strong> {order.address}
                  </div>
                  <div className="order-total">
                    <strong>Total:</strong> {formatRupiah(order.total_price)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        {showCart && <CartModal />}
        {renderCheckoutModal()}
        {orderSuccess && <OrderSuccessModal />}
      </div>
    );
  }

  // --- ADMIN DASHBOARD ---
  if (currentPage === "admin" && user?.role === "admin") {
    return (
      <div className="admin-container">
        <div className="admin-sidebar">
          <div className="admin-logo">
            <span>⚙️</span>
            <h2>Admin Panel</h2>
          </div>
          <nav className="admin-nav">
            <button className={adminTab === "dashboard" ? "active" : ""} onClick={() => setAdminTab("dashboard")}>
              📊 Dashboard
            </button>
            <button className={adminTab === "orders" ? "active" : ""} onClick={() => setAdminTab("orders")}>
              📦 Pesanan
            </button>
            <button className={adminTab === "products" ? "active" : ""} onClick={() => setAdminTab("products")}>
              💊 Produk
            </button>
            <button className={adminTab === "users" ? "active" : ""} onClick={() => setAdminTab("users")}>
              👥 Pengguna
            </button>
          </nav>
          <div className="admin-user-info">
            <span>👤 {user.name}</span>
            <button onClick={handleLogout}>Logout</button>
          </div>
          <button className="btn-back-home" onClick={() => setCurrentPage("landing")}>
            🏠 Kembali ke Website
          </button>
        </div>

        <div className="admin-content">
          {/* Dashboard Tab */}
          {adminTab === "dashboard" && (
            <div className="admin-dashboard">
              <h1>📊 Dashboard</h1>
              {adminStats && (
                <div className="stats-grid">
                  <div className="stat-card">
                    <div className="stat-icon">👥</div>
                    <div className="stat-info">
                      <h3>{adminStats.total_users}</h3>
                      <p>Total Pengguna</p>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">📦</div>
                    <div className="stat-info">
                      <h3>{adminStats.total_orders}</h3>
                      <p>Total Pesanan</p>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">💊</div>
                    <div className="stat-info">
                      <h3>{adminStats.total_medicines}</h3>
                      <p>Total Produk</p>
                    </div>
                  </div>
                  <div className="stat-card">
                    <div className="stat-icon">💰</div>
                    <div className="stat-info">
                      <h3>{formatRupiah(adminStats.total_revenue)}</h3>
                      <p>Total Pendapatan</p>
                    </div>
                  </div>
                  <div className="stat-card pending">
                    <div className="stat-icon">⏳</div>
                    <div className="stat-info">
                      <h3>{adminStats.pending_orders}</h3>
                      <p>Pesanan Pending</p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Orders Tab */}
          {adminTab === "orders" && (
            <div className="admin-orders">
              <h1>📦 Kelola Pesanan</h1>
              <div className="orders-table">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Pelanggan</th>
                      <th>Telepon</th>
                      <th>Total</th>
                      <th>Status</th>
                      <th>Tanggal</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminOrders.map(order => (
                      <tr key={order.id}>
                        <td>#{order.id}</td>
                        <td>{order.customer_name}</td>
                        <td>{order.phone}</td>
                        <td>{formatRupiah(order.total_price)}</td>
                        <td>
                          <span className={`status-badge ${order.status}`}>{order.status}</span>
                        </td>
                        <td>{order.created_at}</td>
                        <td>
                          <select
                            value={order.status}
                            onChange={(e) => updateOrderStatus(order.id, e.target.value)}
                          >
                            <option value="pending">Pending</option>
                            <option value="processing">Processing</option>
                            <option value="shipped">Shipped</option>
                            <option value="delivered">Delivered</option>
                            <option value="cancelled">Cancelled</option>
                          </select>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Products Tab */}
          {adminTab === "products" && (
            <div className="admin-products">
              <div className="products-header">
                <h1>💊 Kelola Produk</h1>
                <button className="btn-add-product" onClick={() => {
                  setMedicineForm({ name: "", description: "", category: "", price: 0, stock: 100, image_url: "" });
                  setEditMedicine(null);
                  setShowAddMedicine(true);
                }}>
                  + Tambah Produk
                </button>
              </div>

              <div className="products-table">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Gambar</th>
                      <th>Nama</th>
                      <th>Kategori</th>
                      <th>Harga</th>
                      <th>Stok</th>
                      <th>Aksi</th>
                    </tr>
                  </thead>
                  <tbody>
                    {medicines.map(med => (
                      <tr key={med.id}>
                        <td>{med.id}</td>
                        <td>
                          <div className="product-thumb">
                            {med.image_url ? (
                              <img
                                src={med.image_url.startsWith('/static') ? `${API_URL}${med.image_url}` : med.image_url}
                                alt={med.name}
                                onError={(e) => { e.target.onerror = null; e.target.src = ''; e.target.parentElement.innerHTML = '<span class="no-image">💊</span>'; }}
                              />
                            ) : (
                              <span className="no-image">💊</span>
                            )}
                          </div>
                        </td>
                        <td>{med.name}</td>
                        <td>{med.category}</td>
                        <td>{formatRupiah(med.price)}</td>
                        <td>{med.stock}</td>
                        <td>
                          <button className="btn-edit" onClick={() => {
                            setMedicineForm({
                              name: med.name,
                              description: med.description,
                              category: med.category,
                              price: med.price,
                              stock: med.stock,
                              image_url: med.image_url || ""
                            });
                            setEditMedicine(med);
                            setShowAddMedicine(true);
                          }}>✏️</button>
                          <button className="btn-delete" onClick={() => handleDeleteMedicine(med.id)}>🗑️</button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Add/Edit Medicine Modal */}
              {showAddMedicine && (
                <div className="modal-overlay" onClick={() => setShowAddMedicine(false)}>
                  <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
                    <button className="modal-close" onClick={() => setShowAddMedicine(false)}>✕</button>
                    <h2>{editMedicine ? "Edit Produk" : "Tambah Produk Baru"}</h2>

                    <div className="form-group">
                      <label>Nama Obat</label>
                      <input
                        type="text"
                        value={medicineForm.name}
                        onChange={(e) => setMedicineForm(prev => ({ ...prev, name: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>Deskripsi</label>
                      <textarea
                        value={medicineForm.description}
                        onChange={(e) => setMedicineForm(prev => ({ ...prev, description: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>Kategori</label>
                      <input
                        type="text"
                        value={medicineForm.category}
                        onChange={(e) => setMedicineForm(prev => ({ ...prev, category: e.target.value }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>Harga (Rp)</label>
                      <input
                        type="number"
                        value={medicineForm.price}
                        onChange={(e) => setMedicineForm(prev => ({ ...prev, price: Number(e.target.value) }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>Stok</label>
                      <input
                        type="number"
                        value={medicineForm.stock}
                        onChange={(e) => setMedicineForm(prev => ({ ...prev, stock: Number(e.target.value) }))}
                      />
                    </div>
                    <div className="form-group">
                      <label>📷 Foto Produk (Opsional)</label>
                      <div className="upload-container">
                        <input
                          type="file"
                          accept="image/*"
                          onChange={handleImageUpload}
                          disabled={imageUploading}
                          id="imageUpload"
                          style={{ display: 'none' }}
                        />
                        <label htmlFor="imageUpload" className="btn-upload">
                          {imageUploading ? "⏳ Mengupload..." : "📤 Upload Baru"}
                        </label>
                        <button
                          type="button"
                          className="btn-gallery"
                          onClick={() => {
                            fetchAvailableImages();
                            setShowImageGallery(true);
                          }}
                        >
                          🖼️ Pilih dari Galeri
                        </button>
                      </div>
                      <span className="upload-hint">Upload file baru atau pilih dari gambar yang sudah ada</span>
                      {medicineForm.image_url && (
                        <div className="image-preview">
                          <img src={`${API_URL}${medicineForm.image_url}`} alt="Preview" onError={(e) => e.target.style.display = 'none'} />
                          <button
                            type="button"
                            className="btn-remove-image"
                            onClick={() => setMedicineForm(prev => ({ ...prev, image_url: "" }))}
                          >
                            ✕ Hapus Gambar
                          </button>
                        </div>
                      )}
                    </div>

                    {/* Image Gallery Modal */}
                    {showImageGallery && (
                      <div className="gallery-overlay" onClick={() => setShowImageGallery(false)}>
                        <div className="gallery-modal" onClick={(e) => e.stopPropagation()}>
                          <button className="modal-close" onClick={() => setShowImageGallery(false)}>✕</button>
                          <h3>🖼️ Pilih Gambar dari Galeri</h3>
                          <p className="gallery-info">{availableImages.length} gambar tersedia</p>
                          <div className="gallery-grid">
                            {availableImages.map((img, idx) => (
                              <div
                                key={idx}
                                className={`gallery-item ${medicineForm.image_url === img.url ? 'selected' : ''}`}
                                onClick={() => {
                                  setMedicineForm(prev => ({ ...prev, image_url: img.url }));
                                  setShowImageGallery(false);
                                }}
                              >
                                <img src={`${API_URL}${img.url}`} alt={img.filename} />
                              </div>
                            ))}
                          </div>
                        </div>
                      </div>
                    )}

                    <button className="btn-save-product" onClick={handleSaveMedicine}>
                      {editMedicine ? "💾 Update" : "💾 Simpan"}
                    </button>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Users Tab */}
          {adminTab === "users" && (
            <div className="admin-users">
              <h1>👥 Kelola Pengguna</h1>
              <div className="users-table">
                <table>
                  <thead>
                    <tr>
                      <th>ID</th>
                      <th>Nama</th>
                      <th>Email</th>
                      <th>Role</th>
                      <th>Terdaftar</th>
                    </tr>
                  </thead>
                  <tbody>
                    {adminUsers.map(u => (
                      <tr key={u.id}>
                        <td>{u.id}</td>
                        <td>{u.name}</td>
                        <td>{u.email}</td>
                        <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
                        <td>{u.created_at}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    );
  }

  // --- HALAMAN LANDING ---
  if (currentPage === "landing") {
    return (
      <div className="landing-container">
        <UserNav />
        <CartButton />
        <div className="app-container">
          <div className="hero-section">
            <div className="hero-logo">🏥💊</div>
            <h1 className="hero-title">HealthBridge AI</h1>
            <p className="hero-subtitle">
              Asisten kesehatan pribadi Anda yang didukung oleh Artificial Intelligence.
              Diagnosa awal cepat, akurat, dan mudah.
            </p>

            <div className="button-group">
              <button className="btn-start" onClick={() => setCurrentPage("consult")}>
                🩺 Mulai Konsultasi
              </button>
              <button className="btn-catalog" onClick={() => setCurrentPage("catalog")}>
                📚 Katalog Penyakit
              </button>
              <button className="btn-store" onClick={() => setCurrentPage("store")}>
                💊 Toko Obat
              </button>
            </div>
          </div>
        </div>
        {showCart && <CartModal />}
        {renderCheckoutModal()}
        {orderSuccess && <OrderSuccessModal />}
      </div>
    );
  }

  // --- HALAMAN TOKO OBAT ---
  if (currentPage === "store") {
    return (
      <div className="store-container">
        <UserNav />
        <CartButton />

        {/* Header */}
        <div className="store-header">
          <button className="btn-back" onClick={() => setCurrentPage("landing")}>
            ⬅ Kembali
          </button>
          <h1>💊 Toko Obat Online</h1>
          <p>Beli obat yang Anda butuhkan dengan mudah</p>

          {/* Search Bar */}
          <div className="search-bar">
            <input
              type="text"
              placeholder="🔍 Cari obat..."
              value={medicineSearch}
              onChange={(e) => setMedicineSearch(e.target.value)}
            />
          </div>

          {/* Category Filter */}
          <div className="category-filter">
            {categories.map(cat => (
              <button
                key={cat}
                className={`category-btn ${selectedCategory === cat ? 'active' : ''}`}
                onClick={() => setSelectedCategory(cat)}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Medicine Grid */}
        <div className="medicine-grid">
          {filteredMedicines.map((medicine) => (
            <div key={medicine.id} className="medicine-card">
              {medicine.image_url ? (
                <div className="medicine-image">
                  <img src={medicine.image_url.startsWith('/static') ? `${API_URL}${medicine.image_url}` : medicine.image_url} alt={medicine.name} onError={(e) => { e.target.onerror = null; e.target.src = ''; e.target.parentElement.innerHTML = '<div class="medicine-icon">💊</div>'; }} />
                </div>
              ) : (
                <div className="medicine-icon">💊</div>
              )}
              <div
                className="medicine-category"
                style={{ backgroundColor: categoryColors[medicine.category] || "#666" }}
              >
                {medicine.category}
              </div>
              <h3 className="medicine-name">{medicine.name}</h3>
              <p className="medicine-desc">{medicine.description}</p>
              <div className="medicine-price">{formatRupiah(medicine.price)}</div>
              <div className="medicine-stock">Stok: {medicine.stock}</div>
              <button
                className="btn-add-cart"
                onClick={() => addToCart(medicine.id, medicine.name)}
                disabled={cartLoading}
              >
                🛒 Tambah ke Keranjang
              </button>
            </div>
          ))}
        </div>

        {showCart && <CartModal />}
        {renderCheckoutModal()}
        {orderSuccess && <OrderSuccessModal />}
      </div>
    );
  }

  // --- HALAMAN KATALOG PENYAKIT ---
  if (currentPage === "catalog") {
    return (
      <div className="catalog-container">
        <UserNav />
        <CartButton />
        {/* Header */}
        <div className="catalog-header">
          <button className="btn-back" onClick={() => setCurrentPage("landing")}>
            ⬅ Kembali
          </button>
          <h1>📚 Katalog Penyakit</h1>
          <p>Pelajari berbagai penyakit dan cara penanganannya</p>

          {/* Search Bar */}
          <div className="search-bar">
            <input
              type="text"
              placeholder="🔍 Cari penyakit, gejala, atau kategori..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
        </div>

        {/* Disease Grid */}
        <div className="disease-grid">
          {filteredDiseases.map((disease) => (
            <div
              key={disease.id}
              className="disease-card"
              onClick={() => setSelectedDisease(disease)}
            >
              <div className="disease-icon">
                {diseaseIcons[disease.name] || "🏥"}
              </div>
              <div
                className="disease-category"
                style={{ backgroundColor: categoryColors[disease.category] || "#666" }}
              >
                {disease.category}
              </div>
              <h3 className="disease-name">{disease.name}</h3>
              <p className="disease-preview">
                {disease.description.substring(0, 80)}...
              </p>
              <button className="btn-detail">Lihat Detail →</button>
            </div>
          ))}
        </div>

        {/* Modal Detail Penyakit */}
        {selectedDisease && (
          <div className="modal-overlay" onClick={() => setSelectedDisease(null)}>
            <div className="modal-content" onClick={(e) => e.stopPropagation()}>
              <button className="modal-close" onClick={() => setSelectedDisease(null)}>✕</button>

              <div className="modal-header">
                <span className="modal-icon">{diseaseIcons[selectedDisease.name] || "🏥"}</span>
                <div>
                  <h2>{selectedDisease.name}</h2>
                  <span
                    className="modal-category"
                    style={{ backgroundColor: categoryColors[selectedDisease.category] }}
                  >
                    {selectedDisease.category}
                  </span>
                </div>
              </div>

              <div className="modal-body">
                <div className="info-section">
                  <h4>📋 Deskripsi</h4>
                  <p>{selectedDisease.description}</p>
                </div>

                <div className="info-section">
                  <h4>🔍 Gejala Umum</h4>
                  <div className="symptom-tags">
                    {selectedDisease.symptoms.split(',').map((symptom, idx) => (
                      <span key={idx} className="symptom-tag">{symptom.trim()}</span>
                    ))}
                  </div>
                </div>

                <div className="info-section">
                  <h4>💊 Penanganan</h4>
                  <p>{selectedDisease.treatment}</p>
                </div>
              </div>

              <button
                className="btn-consult-now"
                onClick={() => {
                  setSelectedDisease(null);
                  setCurrentPage("store");
                }}
              >
                💊 Beli Obat
              </button>
            </div>
          </div>
        )}

        {showCart && <CartModal />}
        {renderCheckoutModal()}
        {orderSuccess && <OrderSuccessModal />}
      </div>
    );
  }

  // --- HALAMAN KONSULTASI ---
  return (
    <div className="app-container consult-container">
      <UserNav />
      <CartButton />
      <div className="nav-buttons">
        <button className="btn-back" onClick={() => setCurrentPage("landing")}>
          ⬅ Kembali
        </button>
        <button className="btn-nav-catalog" onClick={() => setCurrentPage("catalog")}>
          📚 Katalog
        </button>
        <button className="btn-nav-store" onClick={() => setCurrentPage("store")}>
          💊 Toko Obat
        </button>
      </div>

      <h1>🩺 Konsultasi AI</h1>
      <p className="subtitle">Jelaskan keluhan Anda secara detail untuk diagnosa yang akurat</p>

      <div className="form-group">
        <label>Nama Pasien</label>
        <input
          type="text"
          placeholder="Masukkan nama Anda..."
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
      </div>

      <div className="form-group">
        <label>Keluhan Utama</label>
        <textarea
          placeholder="Contoh: Saya merasa pusing berputar, mual, dan keringat dingin sejak 2 hari lalu..."
          value={symptoms}
          onChange={(e) => setSymptoms(e.target.value)}
        ></textarea>
      </div>

      <button
        className="btn-diagnose"
        onClick={handleDiagnose}
        disabled={loading}
      >
        {loading ? "⏳ Sedang Menganalisa..." : "✨ Cek Diagnosa Sekarang"}
      </button>

      {/* Referensi Penyakit - Tampil saat belum ada hasil */}
      {!result && diseases.length > 0 && (
        <div className="disease-reference-section">
          <h3>📋 Referensi Penyakit</h3>
          <p className="reference-subtitle">Klik penyakit untuk melihat gejala dan mengisi form otomatis</p>
          <div className="disease-reference-grid">
            {diseases.slice(0, 15).map((disease) => (
              <div
                key={disease.id}
                className="disease-ref-card"
                onClick={() => {
                  setSymptoms(disease.symptoms);
                  setSelectedDisease(disease);
                }}
              >
                <span className="ref-icon">{diseaseIcons[disease.name] || "🏥"}</span>
                <span className="ref-name">{disease.name}</span>
                <span
                  className="ref-category"
                  style={{ backgroundColor: categoryColors[disease.category] || "#666" }}
                >
                  {disease.category}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Hasil Diagnosa */}
      {result && (
        <div className="result-box-new">
          <div className="result-header">
            <h3>📄 Hasil Analisa untuk <span className="highlight-text">{name}</span></h3>
          </div>

          {result.disease && (
            <div className="disease-main-card">
              <div className="disease-icon-large">
                {diseaseIcons[result.disease.name] || "👁️"}
              </div>
              <div className="disease-info-content">
                <span
                  className="disease-category-badge"
                  style={{ backgroundColor: categoryColors[result.disease.category] || "#2ecc71" }}
                >
                  {result.disease.category}
                </span>
                <h2>{result.disease.name}</h2>
                <p>{result.disease.description}</p>
              </div>
            </div>
          )}

          <div className="result-section">
            <div className="section-label">🤖 Diagnosa AI:</div>
            <div className="diagnosis-alert">
              {result.diagnosis}
            </div>
          </div>

          <div className="result-section">
            <div className="section-label">💡 Saran & Tindakan:</div>
            <div className="advice-alert">
              {result.advice}
            </div>
          </div>

          {result.disease && (
            <>
              <div className="result-section">
                <div className="section-label">📝 Gejala Terkait:</div>
                <div className="tag-container">
                  {result.disease.symptoms.split(',').map((sym, idx) => (
                    <span key={idx} className="tag-purple">{sym.trim()}</span>
                  ))}
                </div>
              </div>

              <div className="result-section">
                <div className="section-label">💊 Rekomendasi Obat:</div>
                <div className="tag-container">
                  {result.disease.medicines.split(',').map((med, idx) => (
                    <span
                      key={idx}
                      className="tag-teal"
                      onClick={() => {
                        setMedicineSearch(med.trim());
                        setCurrentPage("store");
                      }}
                    >
                      {med.trim()}
                    </span>
                  ))}
                </div>
              </div>
            </>
          )}

          <div className="warning-banner">
            ⚠️ Konsultasikan dengan dokter atau apoteker sebelum menggunakan obat
          </div>
        </div>
      )}

      {showCart && <CartModal />}
      {renderCheckoutModal()}
      {orderSuccess && <OrderSuccessModal />}
      {selectedMedicine && (
        <div className="modal-overlay" onClick={() => setSelectedMedicine(null)}>
          <div className="modal-content medicine-modal" onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedMedicine(null)}>✕</button>
            <div className="modal-header">
              <span className="modal-icon">💊</span>
              <div>
                <h2>{selectedMedicine}</h2>
              </div>
            </div>
            <div className="modal-body">
              <p>Klik tombol di bawah untuk membeli obat ini di toko.</p>
            </div>
            <button
              className="btn-consult-now"
              onClick={() => {
                setSelectedMedicine(null);
                setCurrentPage("store");
              }}
            >
              🏪 Beli di Toko Obat
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;