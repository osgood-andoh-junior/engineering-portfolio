"""Frozen initial PostgreSQL schema; generated offline, review before migration."""

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        "\nCREATE TABLE categories (\n\tslug VARCHAR(100) NOT NULL, \n\tname VARCHAR(140) NOT NULL, \n\tdescription TEXT NOT NULL, \n\ticon VARCHAR(30) NOT NULL, \n\tcolor VARCHAR(7) NOT NULL, \n\tparent_id UUID, \n\tarchived BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_categories PRIMARY KEY (id), \n\tCONSTRAINT uq_categories_slug UNIQUE (slug), \n\tCONSTRAINT fk_categories_parent_id_categories FOREIGN KEY(parent_id) REFERENCES categories (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE rate_limits (\n\tkey VARCHAR(64) NOT NULL, \n\tcount INTEGER NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_rate_limits PRIMARY KEY (key)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_rate_limits_expires_at ON rate_limits (expires_at)")
    op.execute(
        "\nCREATE TABLE roles (\n\tname VARCHAR(30) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_roles PRIMARY KEY (id), \n\tCONSTRAINT uq_roles_name UNIQUE (name)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE users (\n\temail VARCHAR(254) NOT NULL, \n\tpassword_hash VARCHAR(500) NOT NULL, \n\tverified BOOLEAN NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_users PRIMARY KEY (id), \n\tCONSTRAINT uq_users_email UNIQUE (email)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE account_tokens (\n\tuser_id UUID NOT NULL, \n\ttoken_hash VARCHAR(64) NOT NULL, \n\tpurpose VARCHAR(20) NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tused BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_account_tokens PRIMARY KEY (id), \n\tCONSTRAINT fk_account_tokens_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tCONSTRAINT uq_account_tokens_token_hash UNIQUE (token_hash)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_account_tokens_user_id ON account_tokens (user_id)")
    op.execute(
        "\nCREATE TABLE addresses (\n\tuser_id UUID NOT NULL, \n\tstreet VARCHAR(200) NOT NULL, \n\tregion VARCHAR(80) NOT NULL, \n\tcity VARCHAR(100) NOT NULL, \n\tphone VARCHAR(20) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_addresses PRIMARY KEY (id), \n\tCONSTRAINT fk_addresses_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)\n\n"
    )
    op.execute("CREATE INDEX ix_addresses_user_id ON addresses (user_id)")
    op.execute(
        "\nCREATE TABLE audit_logs (\n\tactor_id UUID, \n\taction VARCHAR(80) NOT NULL, \n\tresource_id VARCHAR(100) NOT NULL, \n\tdetails JSONB NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_audit_logs PRIMARY KEY (id), \n\tCONSTRAINT fk_audit_logs_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_audit_logs_actor_id ON audit_logs (actor_id)")
    op.execute(
        "\nCREATE TABLE customer_profiles (\n\tuser_id UUID NOT NULL, \n\tname VARCHAR(160) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_customer_profiles PRIMARY KEY (id), \n\tCONSTRAINT uq_customer_profiles_user_id UNIQUE (user_id), \n\tCONSTRAINT fk_customer_profiles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE orders (\n\tuser_id UUID NOT NULL, \n\treference VARCHAR(40) NOT NULL, \n\tidempotency_key VARCHAR(100) NOT NULL, \n\trequest_hash VARCHAR(64) NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tsubtotal_minor BIGINT NOT NULL, \n\tshipping_minor BIGINT NOT NULL, \n\ttotal_minor BIGINT NOT NULL, \n\tcurrency VARCHAR(3) NOT NULL, \n\tcustomer JSONB NOT NULL, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_orders PRIMARY KEY (id), \n\tCONSTRAINT uq_orders_user_id UNIQUE (user_id, idempotency_key), \n\tCONSTRAINT ck_orders_totals_consistent CHECK (subtotal_minor >= 0 AND shipping_minor >= 0 AND total_minor = subtotal_minor + shipping_minor), \n\tCONSTRAINT ck_orders_order_status CHECK (status IN ('pending_payment','paid','processing','shipped','delivered','cancelled','refunded')), \n\tCONSTRAINT fk_orders_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), \n\tCONSTRAINT uq_orders_reference UNIQUE (reference)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_orders_expires_at ON orders (expires_at)")
    op.execute("CREATE INDEX ix_orders_user_id ON orders (user_id)")
    op.execute(
        "\nCREATE TABLE products (\n\tcategory_id UUID NOT NULL, \n\tslug VARCHAR(160) NOT NULL, \n\tname VARCHAR(200) NOT NULL, \n\tdescription TEXT NOT NULL, \n\tprice_minor BIGINT NOT NULL, \n\tstatus VARCHAR(20) NOT NULL, \n\tdemonstration BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_products PRIMARY KEY (id), \n\tCONSTRAINT ck_products_price_nonnegative CHECK (price_minor >= 0), \n\tCONSTRAINT ck_products_publication_status CHECK (status IN ('draft','published','archived')), \n\tCONSTRAINT fk_products_category_id_categories FOREIGN KEY(category_id) REFERENCES categories (id), \n\tCONSTRAINT uq_products_slug UNIQUE (slug)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_products_category_status ON products (category_id, status)")
    op.execute(
        "\nCREATE TABLE sessions (\n\ttoken_hash VARCHAR(64) NOT NULL, \n\tcsrf VARCHAR(100) NOT NULL, \n\tuser_id UUID, \n\texpires_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_sessions PRIMARY KEY (id), \n\tCONSTRAINT uq_sessions_token_hash UNIQUE (token_hash), \n\tCONSTRAINT fk_sessions_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE\n)\n\n"
    )
    op.execute("CREATE INDEX ix_sessions_expires_at ON sessions (expires_at)")
    op.execute("CREATE INDEX ix_sessions_user_id ON sessions (user_id)")
    op.execute(
        "\nCREATE TABLE user_roles (\n\tuser_id UUID NOT NULL, \n\trole_id UUID NOT NULL, \n\tCONSTRAINT pk_user_roles PRIMARY KEY (user_id, role_id), \n\tCONSTRAINT fk_user_roles_user_id_users FOREIGN KEY(user_id) REFERENCES users (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_user_roles_role_id_roles FOREIGN KEY(role_id) REFERENCES roles (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE carts (\n\tuser_id UUID, \n\tsession_id UUID, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_carts PRIMARY KEY (id), \n\tCONSTRAINT uq_carts_user_id UNIQUE (user_id), \n\tCONSTRAINT fk_carts_user_id_users FOREIGN KEY(user_id) REFERENCES users (id), \n\tCONSTRAINT uq_carts_session_id UNIQUE (session_id), \n\tCONSTRAINT fk_carts_session_id_sessions FOREIGN KEY(session_id) REFERENCES sessions (id) ON DELETE CASCADE\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE payments (\n\torder_id UUID NOT NULL, \n\tprovider_reference VARCHAR(200), \n\tprovider VARCHAR(40) NOT NULL, \n\tamount_minor BIGINT NOT NULL, \n\tstatus VARCHAR(30) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_payments PRIMARY KEY (id), \n\tCONSTRAINT ck_payments_amount_nonnegative CHECK (amount_minor >= 0), \n\tCONSTRAINT fk_payments_order_id_orders FOREIGN KEY(order_id) REFERENCES orders (id), \n\tCONSTRAINT uq_payments_provider_reference UNIQUE (provider_reference)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_payments_order_id ON payments (order_id)")
    op.execute(
        "\nCREATE TABLE product_images (\n\tproduct_id UUID NOT NULL, \n\tpath VARCHAR(300) NOT NULL, \n\talt VARCHAR(300) NOT NULL, \n\tposition INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_product_images PRIMARY KEY (id), \n\tCONSTRAINT fk_product_images_product_id_products FOREIGN KEY(product_id) REFERENCES products (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_product_images_product_id ON product_images (product_id)")
    op.execute(
        "\nCREATE TABLE product_variants (\n\tproduct_id UUID NOT NULL, \n\tsku VARCHAR(80) NOT NULL, \n\tname VARCHAR(100) NOT NULL, \n\tactive BOOLEAN NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_product_variants PRIMARY KEY (id), \n\tCONSTRAINT fk_product_variants_product_id_products FOREIGN KEY(product_id) REFERENCES products (id), \n\tCONSTRAINT uq_product_variants_sku UNIQUE (sku)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_product_variants_product_id ON product_variants (product_id)")
    op.execute(
        "\nCREATE TABLE shipments (\n\torder_id UUID NOT NULL, \n\ttracking_reference VARCHAR(200), \n\tstatus VARCHAR(30) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_shipments PRIMARY KEY (id), \n\tCONSTRAINT uq_shipments_order_id UNIQUE (order_id), \n\tCONSTRAINT fk_shipments_order_id_orders FOREIGN KEY(order_id) REFERENCES orders (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE cart_items (\n\tcart_id UUID NOT NULL, \n\tvariant_id UUID NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_cart_items PRIMARY KEY (id), \n\tCONSTRAINT uq_cart_items_cart_id UNIQUE (cart_id, variant_id), \n\tCONSTRAINT ck_cart_items_quantity_bounds CHECK (quantity BETWEEN 1 AND 20), \n\tCONSTRAINT fk_cart_items_cart_id_carts FOREIGN KEY(cart_id) REFERENCES carts (id) ON DELETE CASCADE, \n\tCONSTRAINT fk_cart_items_variant_id_product_variants FOREIGN KEY(variant_id) REFERENCES product_variants (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_cart_items_cart_id ON cart_items (cart_id)")
    op.execute(
        "\nCREATE TABLE inventory (\n\tvariant_id UUID NOT NULL, \n\tquantity INTEGER NOT NULL, \n\treserved INTEGER NOT NULL, \n\tlow_stock_threshold INTEGER NOT NULL, \n\tCONSTRAINT pk_inventory PRIMARY KEY (variant_id), \n\tCONSTRAINT ck_inventory_stock_bounds CHECK (quantity >= 0 AND reserved >= 0 AND reserved <= quantity), \n\tCONSTRAINT ck_inventory_threshold_nonnegative CHECK (low_stock_threshold >= 0), \n\tCONSTRAINT fk_inventory_variant_id_product_variants FOREIGN KEY(variant_id) REFERENCES product_variants (id)\n)\n\n"
    )
    op.execute(
        "\nCREATE TABLE inventory_movements (\n\tvariant_id UUID NOT NULL, \n\tdelta INTEGER NOT NULL, \n\treserved_delta INTEGER NOT NULL, \n\treason VARCHAR(200) NOT NULL, \n\tactor_id UUID, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_inventory_movements PRIMARY KEY (id), \n\tCONSTRAINT fk_inventory_movements_variant_id_product_variants FOREIGN KEY(variant_id) REFERENCES product_variants (id), \n\tCONSTRAINT fk_inventory_movements_actor_id_users FOREIGN KEY(actor_id) REFERENCES users (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_inventory_movements_variant_id ON inventory_movements (variant_id)")
    op.execute(
        "\nCREATE TABLE order_items (\n\torder_id UUID NOT NULL, \n\tvariant_id UUID NOT NULL, \n\tproduct_name VARCHAR(200) NOT NULL, \n\tsku VARCHAR(80) NOT NULL, \n\tquantity INTEGER NOT NULL, \n\tunit_price_minor BIGINT NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_order_items PRIMARY KEY (id), \n\tCONSTRAINT ck_order_items_line_values CHECK (quantity > 0 AND unit_price_minor >= 0), \n\tCONSTRAINT fk_order_items_order_id_orders FOREIGN KEY(order_id) REFERENCES orders (id), \n\tCONSTRAINT fk_order_items_variant_id_product_variants FOREIGN KEY(variant_id) REFERENCES product_variants (id)\n)\n\n"
    )
    op.execute("CREATE INDEX ix_order_items_order_id ON order_items (order_id)")
    op.execute(
        "\nCREATE TABLE payment_events (\n\tpayment_id UUID NOT NULL, \n\tprovider VARCHAR(40) NOT NULL, \n\tevent_id VARCHAR(200) NOT NULL, \n\tkind VARCHAR(40) NOT NULL, \n\tid UUID NOT NULL, \n\tcreated_at TIMESTAMP WITH TIME ZONE NOT NULL, \n\tCONSTRAINT pk_payment_events PRIMARY KEY (id), \n\tCONSTRAINT uq_payment_events_provider UNIQUE (provider, event_id), \n\tCONSTRAINT fk_payment_events_payment_id_payments FOREIGN KEY(payment_id) REFERENCES payments (id)\n)\n\n"
    )


def downgrade():
    op.drop_table("payment_events")
    op.drop_table("order_items")
    op.drop_table("inventory_movements")
    op.drop_table("inventory")
    op.drop_table("cart_items")
    op.drop_table("shipments")
    op.drop_table("product_variants")
    op.drop_table("product_images")
    op.drop_table("payments")
    op.drop_table("carts")
    op.drop_table("user_roles")
    op.drop_table("sessions")
    op.drop_table("products")
    op.drop_table("orders")
    op.drop_table("customer_profiles")
    op.drop_table("audit_logs")
    op.drop_table("addresses")
    op.drop_table("account_tokens")
    op.drop_table("users")
    op.drop_table("roles")
    op.drop_table("rate_limits")
    op.drop_table("categories")
