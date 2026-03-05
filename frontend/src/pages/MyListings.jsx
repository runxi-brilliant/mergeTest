import { useState, useEffect, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import ProductCard from "../components/ProductCard";
import { API_BASE, authFetch } from "../api";
import "./Home.css";

function MyListings() {
  const navigate = useNavigate();
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [favoritedIds, setFavoritedIds] = useState(new Set());

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      try {
        const res = await authFetch(`${API_BASE}/products/user/me`);
        if (!cancelled) {
          if (res.ok) {
            const list = await res.json();
            setProducts(list);
          } else {
            setError("Failed to load your products");
          }
        }
      } catch (e) {
        if (!cancelled) setError(e.message || "Failed to load");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function fetchFavorites() {
      try {
        const res = await authFetch(`${API_BASE}/favorites`);
        if (cancelled) return;
        if (res.ok) {
          const list = await res.json();
          setFavoritedIds(new Set((list || []).map((p) => String(p.id))));
        }
      } catch {
        if (!cancelled) setFavoritedIds(new Set());
      }
    }
    fetchFavorites();
    return () => { cancelled = true; };
  }, []);

  async function handleToggleFavorite(productId) {
    const id = String(productId);
    const isFav = favoritedIds.has(id);
    try {
      if (isFav) {
        const res = await authFetch(`${API_BASE}/products/${productId}/favorite`, { method: "DELETE" });
        if (res.ok) setFavoritedIds((prev) => { const s = new Set(prev); s.delete(id); return s; });
      } else {
        const res = await authFetch(`${API_BASE}/products/${productId}/favorite`, { method: "POST" });
        if (res.ok) setFavoritedIds((prev) => new Set([...prev, id]));
      }
    } catch (_) {}
  }

  const normalizedProducts = useMemo(() => {
    return products.map((p) => ({
      id: p.id,
      name: p.title,
      price: p.price,
      condition: p.condition || "good",
      category: p.category,
      image: p.images?.length
        ? (p.images[0].startsWith("http") ? p.images[0] : `${API_BASE}${p.images[0]}`)
        : "https://placehold.co/400x400",
      isMine: true,
    }));
  }, [products]);

  return (
    <div className="home">
      <div className="home-header">
        <div>
          <h1 className="home-title">My Listings</h1>
          <p className="home-subtitle">Products you have published</p>
        </div>

        <div style={{ display: "flex", gap: 12, flexWrap: "wrap" }}>
          <button
            className="logout-btn"
            onClick={() => navigate("/home")}
            style={{ background: "#64748b" }}
          >
            Discovery
          </button>
          <button
            className="logout-btn"
            onClick={() => navigate("/favorites")}
            style={{ background: "#e11d48" }}
          >
            My Favorites
          </button>
          <button
            className="logout-btn"
            onClick={() => navigate("/orders")}
            style={{ background: "#2563eb" }}
          >
            My Orders
          </button>
        </div>
      </div>

      <div className="product-list">
        {loading && <p style={{ marginTop: 20 }}>Loading...</p>}
        {error && <p style={{ marginTop: 20, color: "red" }}>{error}</p>}
        {!loading && !error && normalizedProducts.map((product) => (
          <ProductCard
            key={product.id}
            product={product}
            isFavorited={favoritedIds.has(String(product.id))}
            isMine={true}
            onToggleFavorite={handleToggleFavorite}
          />
        ))}

        {!loading && !error && normalizedProducts.length === 0 && (
          <p style={{ marginTop: 20, color: "#64748b" }}>
            You haven&apos;t published any products yet. Go to Discovery to browse, or publish from there.
          </p>
        )}
      </div>
    </div>
  );
}

export default MyListings;
