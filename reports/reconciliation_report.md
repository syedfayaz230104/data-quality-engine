# Data Quality & Pipeline Reconciliation Report

**Generated At:** 2026-10-30 05:53:49.144802 (UTC)  
**Run ID:** `RUN_20261030_055349_bcb42a`  
**Pipeline Status:** `PARTIAL_SUCCESS`  
**Execution Duration:** 0.5289 seconds  

---

## 1. Source-to-Target Reconciliation Equation
Every record processed by the pipeline is deterministically verified:
$$\\text{Total Input Records} = \\text{Target Published Records} + \\text{Quarantined Records}$$

| Dataset | Target Clean Rows | Quarantined Rows | Total Accounted | Reconciliation Status |
| :--- | :--- | :--- | :--- | :--- |
| `customers` | 50 | 3 | 53 | **BALANCED** |
| `products` | 40 | 2 | 42 | **BALANCED** |
| `orders` | 100 | 2 | 102 | **BALANCED** |
| `order_items` | 200 | 3 | 203 | **BALANCED** |

---

## 2. Referential Integrity Verification
Asserts zero orphan foreign keys in the curated analytical warehouse tables.

| Integrity Check | Target Table | Foreign Key | Orphan Records Found | Result |
| :--- | :--- | :--- | :--- | :--- |
| `orders_customer_id_fk` | `orders` | `customer_id` | 0 | ✅ PASSED |
| `order_items_order_id_fk` | `order_items` | `order_id` | 0 | ✅ PASSED |
| `order_items_product_id_fk` | `order_items` | `product_id` | 0 | ✅ PASSED |

---

## 3. Uniqueness Verification
Asserts zero duplicate primary keys in published warehouse models.

| Table | Primary Key | Duplicate Count | Result |
| :--- | :--- | :--- | :--- |
| `customers` | `customer_id` | 0 | ✅ PASSED |
| `products` | `product_id` | 0 | ✅ PASSED |
| `orders` | `order_id` | 0 | ✅ PASSED |
| `order_items` | `item_id` | 0 | ✅ PASSED |

---

## 4. Financial & Metric Aggregates
- **Total Orders Clean Ingested:** 100
- **Gross Order Header Volume:** \$74,100.34
- **Gross Line Items Volume:** \$180,646.80
- **Quarantined Rejection Audit Records:** 10 records captured with full error descriptions.

---

## 5. Audit Log Summary
All evaluations are logged to the `dq_audit_log` and `pipeline_runs` tables.
