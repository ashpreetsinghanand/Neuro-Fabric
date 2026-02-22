import React from 'react';

function App() {
    return (
        <div className="app">
            <header className="header">
                <h1>🚲 Bike Store</h1>
                <nav>
                    <a href="/">Home</a>
                    <a href="/products">Products</a>
                    <a href="/orders">Orders</a>
                    <a href="/inventory">Inventory</a>
                </nav>
            </header>
            <main>
                <section className="hero">
                    <h2>Premium Bicycles for Every Rider</h2>
                    <p>Shop from Trek, Giant, Specialized, and more.</p>
                </section>
                <section className="featured">
                    <h3>Featured Products</h3>
                    <div className="product-grid">
                        <ProductCard name="Trek 820" price={379.99} category="Mountain" />
                        <ProductCard name="Specialized S-Works" price={4499.99} category="Road" />
                        <ProductCard name="Electra Townie" price={489.99} category="Cruiser" />
                        <ProductCard name="Trek Conduit+" price={2799.99} category="Electric" />
                    </div>
                </section>
            </main>
        </div>
    );
}

function ProductCard({ name, price, category }) {
    return (
        <div className="product-card">
            <span className="category-badge">{category}</span>
            <h4>{name}</h4>
            <p className="price">${price.toLocaleString()}</p>
            <button>Add to Cart</button>
        </div>
    );
}

export default App;
