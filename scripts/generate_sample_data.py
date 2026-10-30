import os
import json
import random
import argparse
from datetime import datetime, timezone, timedelta

def generate_datasets(target_dir: str, ground_truth_file: str, scale: str = "small", seed: int = 42):
    random.seed(seed)
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(os.path.dirname(ground_truth_file), exist_ok=True)

    base_time = datetime(2026, 10, 20, 10, 0, 0, tzinfo=timezone.utc)

    if scale == "small":
        num_customers = 50
        num_products = 40
        num_orders = 100
        num_items = 200
    elif scale == "medium":
        num_customers = 500
        num_products = 200
        num_orders = 2000
        num_items = 5000
    elif scale == "large":
        num_customers = 15000
        num_products = 5000
        num_orders = 40000
        num_items = 100000
    else:
        raise ValueError(f"Unknown scale: {scale}")

    ground_truth = {
        "metadata": {
            "scale": scale,
            "seed": seed,
            "generated_at": datetime.now(timezone.utc).isoformat()
        },
        "expected_quarantines": [],
        "expected_clean_counts": {}
    }

    # ------------------------------------------------------------------
    # 1. Customers Generation
    # ------------------------------------------------------------------
    customers = []
    countries = ["US", "CA", "GB", "DE", "FR", "IN", "JP", "AU"]

    for i in range(1, num_customers + 1):
        cust_id = f"CUST_{i:06d}"
        created = (base_time - timedelta(days=random.randint(10, 300))).isoformat()
        customers.append({
            "customer_id": cust_id,
            "first_name": f"User_{i}",
            "last_name": f"Test_{i}",
            "email": f"user{i}@example.com",
            "country_code": random.choice(countries),
            "status": "ACTIVE",
            "created_at": created
        })

    if scale == "small":
        # Inject Deliberate Edge Cases into Customers:
        # Edge 1: Missing required email
        cust_err_1 = {
            "customer_id": "CUST_ERR_0001",
            "first_name": "NoEmail",
            "last_name": "User",
            "email": None,
            "country_code": "US",
            "status": "ACTIVE",
            "created_at": base_time.isoformat()
        }
        customers.append(cust_err_1)
        ground_truth["expected_quarantines"].append({
            "dataset": "customers",
            "key": "CUST_ERR_0001",
            "reason": "Missing or null required field: 'email'"
        })

        # Edge 2: Duplicate Customer ID
        cust_dup = dict(customers[0])
        cust_dup["email"] = "duplicate_email@test.com"
        customers.append(cust_dup)
        ground_truth["expected_quarantines"].append({
            "dataset": "customers",
            "key": customers[0]["customer_id"],
            "reason": "Duplicate key detected"
        })

        # Edge 3: Invalid customer status
        cust_err_status = {
            "customer_id": "CUST_ERR_STATUS",
            "first_name": "Bad",
            "last_name": "Status",
            "email": "badstatus@test.com",
            "country_code": "US",
            "status": "BOGUS_STATUS",
            "created_at": base_time.isoformat()
        }
        customers.append(cust_err_status)
        ground_truth["expected_quarantines"].append({
            "dataset": "customers",
            "key": "CUST_ERR_STATUS",
            "reason": "Invalid lifecycle status"
        })

    # ------------------------------------------------------------------
    # 2. Products Generation
    # ------------------------------------------------------------------
    products = []
    categories = ["ELECTRONICS", "APPAREL", "HOME", "BOOKS", "SPORTS"]

    for i in range(1, num_products + 1):
        prod_id = f"PROD_{i:05d}"
        products.append({
            "product_id": prod_id,
            "name": f"Product Item {i}",
            "category": random.choice(categories),
            "unit_price": round(random.uniform(5.0, 500.0), 2),
            "stock_quantity": random.randint(10, 1000),
            "is_active": True,
            "created_at": (base_time - timedelta(days=200)).isoformat()
        })

    if scale == "small":
        # Inject Deliberate Edge Cases into Products:
        # Edge 4: Negative Unit Price
        prod_neg_price = {
            "product_id": "PROD_ERR_NEGPRICE",
            "name": "Invalid Negative Price",
            "category": "ELECTRONICS",
            "unit_price": -25.50,
            "stock_quantity": 50,
            "is_active": True,
            "created_at": base_time.isoformat()
        }
        products.append(prod_neg_price)
        ground_truth["expected_quarantines"].append({
            "dataset": "products",
            "key": "PROD_ERR_NEGPRICE",
            "reason": "unit_price below min_value"
        })

        # Edge 5: Duplicate Product ID
        prod_dup = dict(products[0])
        prod_dup["name"] = "Duplicate Product Name"
        products.append(prod_dup)
        ground_truth["expected_quarantines"].append({
            "dataset": "products",
            "key": products[0]["product_id"],
            "reason": "Duplicate product ID"
        })

    # ------------------------------------------------------------------
    # 3. Orders Generation
    # ------------------------------------------------------------------
    orders = []
    order_statuses = ["PENDING", "CONFIRMED", "SHIPPED", "DELIVERED"]
    payment_methods = ["CREDIT_CARD", "PAYPAL", "WIRE", "APPLE_PAY"]
    valid_cust_ids = [c["customer_id"] for c in customers if not c["customer_id"].startswith("CUST_ERR")]

    for i in range(1, num_orders + 1):
        order_id = f"ORD_{i:07d}"
        cust_id = random.choice(valid_cust_ids)
        order_dt = base_time - timedelta(days=random.randint(1, 100), hours=random.randint(0, 23))
        orders.append({
            "order_id": order_id,
            "customer_id": cust_id,
            "order_date": order_dt.isoformat(),
            "status": random.choice(order_statuses),
            "total_amount": round(random.uniform(20.0, 1500.0), 2),
            "payment_method": random.choice(payment_methods),
            "created_at": order_dt.isoformat()
        })

    if scale == "small":
        # Inject Deliberate Edge Cases into Orders:
        # Edge 6: Invalid Foreign Key (Non-existent Customer)
        ord_orphan = {
            "order_id": "ORD_ERR_ORPHAN",
            "customer_id": "CUST_NON_EXISTENT_9999",
            "order_date": base_time.isoformat(),
            "status": "CONFIRMED",
            "total_amount": 199.99,
            "payment_method": "CREDIT_CARD",
            "created_at": base_time.isoformat()
        }
        orders.append(ord_orphan)
        ground_truth["expected_quarantines"].append({
            "dataset": "orders",
            "key": "ORD_ERR_ORPHAN",
            "reason": "Foreign key customer_id does not exist"
        })

        # Edge 7: Freshness violation (Future-dated order)
        ord_future = {
            "order_id": "ORD_ERR_FUTURE",
            "customer_id": valid_cust_ids[0],
            "order_date": (datetime.now(timezone.utc) + timedelta(days=120)).isoformat(),
            "status": "PENDING",
            "total_amount": 50.00,
            "payment_method": "PAYPAL",
            "created_at": (datetime.now(timezone.utc) + timedelta(days=120)).isoformat()
        }
        orders.append(ord_future)
        ground_truth["expected_quarantines"].append({
            "dataset": "orders",
            "key": "ORD_ERR_FUTURE",
            "reason": "Order date in future"
        })

    # ------------------------------------------------------------------
    # 4. Order Items Generation
    # ------------------------------------------------------------------
    order_items = []
    valid_order_ids = [o["order_id"] for o in orders if not o["order_id"].startswith("ORD_ERR")]
    valid_prod_ids = [p["product_id"] for p in products if not p["product_id"].startswith("PROD_ERR")]
    prod_price_map = {p["product_id"]: p["unit_price"] for p in products}

    for i in range(1, num_items + 1):
        item_id = f"ITEM_{i:08d}"
        ord_id = random.choice(valid_order_ids)
        prod_id = random.choice(valid_prod_ids)
        qty = random.randint(1, 5)
        u_price = prod_price_map.get(prod_id, 25.0)
        l_total = round(qty * u_price, 2)
        order_items.append({
            "item_id": item_id,
            "order_id": ord_id,
            "product_id": prod_id,
            "quantity": qty,
            "unit_price": u_price,
            "line_total": l_total,
            "created_at": base_time.isoformat()
        })

    if scale == "small":
        # Inject Deliberate Edge Cases into Order Items:
        # Edge 8: Line Total Math Inconsistency (Calculated custom rule failure)
        item_bad_math = {
            "item_id": "ITEM_ERR_BAD_MATH",
            "order_id": valid_order_ids[0],
            "product_id": valid_prod_ids[0],
            "quantity": 3,
            "unit_price": 50.00,
            "line_total": 999.99, # Should be 150.00
            "created_at": base_time.isoformat()
        }
        order_items.append(item_bad_math)
        ground_truth["expected_quarantines"].append({
            "dataset": "order_items",
            "key": "ITEM_ERR_BAD_MATH",
            "reason": "Math inconsistency line_total != qty * unit_price"
        })

        # Edge 9: Invalid Foreign Key (Non-existent product_id)
        item_bad_fk = {
            "item_id": "ITEM_ERR_BAD_PROD_FK",
            "order_id": valid_order_ids[0],
            "product_id": "PROD_GHOST_9999",
            "quantity": 1,
            "unit_price": 10.00,
            "line_total": 10.00,
            "created_at": base_time.isoformat()
        }
        order_items.append(item_bad_fk)
        ground_truth["expected_quarantines"].append({
            "dataset": "order_items",
            "key": "ITEM_ERR_BAD_PROD_FK",
            "reason": "Foreign key product_id does not exist"
        })

        # Edge 10: Range Violation (Zero quantity)
        item_zero_qty = {
            "item_id": "ITEM_ERR_ZERO_QTY",
            "order_id": valid_order_ids[0],
            "product_id": valid_prod_ids[0],
            "quantity": 0, # Violates min_value: 1
            "unit_price": 20.00,
            "line_total": 0.00,
            "created_at": base_time.isoformat()
        }
        order_items.append(item_zero_qty)
        ground_truth["expected_quarantines"].append({
            "dataset": "order_items",
            "key": "ITEM_ERR_ZERO_QTY",
            "reason": "Quantity below minimum allowed"
        })

    # Summary of clean expectations
    ground_truth["expected_clean_counts"] = {
        "customers": num_customers,
        "products": num_products,
        "orders": num_orders,
        "order_items": num_items
    }

    # Write input files
    with open(os.path.join(target_dir, "customers.json"), "w", encoding="utf-8") as f:
        json.dump(customers, f, indent=2)

    with open(os.path.join(target_dir, "products.json"), "w", encoding="utf-8") as f:
        json.dump(products, f, indent=2)

    with open(os.path.join(target_dir, "orders.json"), "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2)

    with open(os.path.join(target_dir, "order_items.json"), "w", encoding="utf-8") as f:
        json.dump(order_items, f, indent=2)

    with open(ground_truth_file, "w", encoding="utf-8") as f:
        json.dump(ground_truth, f, indent=2)

    print(f"Generated {scale} dataset in '{target_dir}':")
    print(f"  Customers: {len(customers)} records")
    print(f"  Products: {len(products)} records")
    print(f"  Orders: {len(orders)} records")
    print(f"  Order Items: {len(order_items)} records")
    print(f"  Expected Quarantined: {len(ground_truth['expected_quarantines'])} records")
    print(f"  Ground truth saved to: '{ground_truth_file}'")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate synthetic sample data with configurable volume and edge cases.")
    parser.add_argument("--scale", choices=["small", "medium", "large"], default="small", help="Scale of data generation")
    parser.add_argument("--out-dir", default="data/input/small", help="Target output directory")
    parser.add_argument("--ground-truth", default="data/input/ground_truth/expected_reconciliation.json", help="Ground truth path")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed")
    args = parser.parse_args()

    generate_datasets(args.out_dir, args.ground_truth, scale=args.scale, seed=args.seed)
