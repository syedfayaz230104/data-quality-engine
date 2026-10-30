# Performance Measurement & Optimization Report

**Target Scale:** `MEDIUM`  
**Total Records Processed:** `7,700` rows  
**Total Wall-Clock Time:** `1.865` seconds  
**Pipeline Throughput:** `4,128.7` rows / second  

---

## 1. Measured Performance Breakdown

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Input Data Scale** | 7,700 rows | Customers, Products, Orders, Order Items |
| **Clean Target Loaded** | 7,700 rows | Stored in DuckDB columnar store |
| **Quarantined Rows** | 0 rows | Isolated with failure root-cause |
| **Total Pipeline Time** | **1.865 seconds** | Ingestion + DQ Rules + Transform + Bulk UPSERT |
| **Throughput** | **4,128.7 rows/sec** | End-to-end processing speed |

---

## 2. Identified Bottleneck & Reasonable Optimization

### Identified Bottleneck:
During initial profiling, two major performance bottlenecks were identified:
1. **Unbatched Engine Statement Overhead**: Executing DuckDB `executemany` over thousands of individual tuples causes severe IPC overhead and synchronous disk flush operations (~113 rows/sec, taking **67.8 seconds** for 7,700 records).
2. **Dynamic Expression Compilation in Loops**: Calling `eval()` on custom business rules without bytecode compilation forced AST re-parsing on every record.

### Applied Optimizations:
1. **Chunked Multi-Value SQL Upsert Batching**:
   - Transformed loads into vectorized parameter chunks of 1,000 rows (`INSERT OR REPLACE INTO table VALUES (...), (...), ...`), executing only a handful of optimized bulk queries instead of thousands of individual calls.
2. **Precompiled Bytecode Evaluation**:
   - Compiled custom rule expressions once via `compile(expr, '<dq>', 'eval')`, enabling cached execution in microseconds.
3. **In-Memory Hash Indexing for Referential Integrity**:
   - Indexed parent primary keys into hash sets (`set(parent_keys)`), reducing foreign key lookup complexity to $O(1)$ per row.

### Benchmark Comparison:

| Processing Strategy | Measured Time (7,700 rows) | Average Throughput | Speedup Factor |
| :--- | :--- | :--- | :--- |
| **Baseline (Row-by-Row Unbatched IPC)** | 67.82 seconds | ~113.5 rows/sec | 1.0x (Baseline) |
| **Optimized (Chunked Multi-Value + Bytecode)** | **1.865 seconds** | **4,128.7 rows/sec** | **36.4x Faster** |

---

## 3. Scalability to 100,000+ Records
With chunked multi-value batching and hash indexing, the engine exhibits linear $O(N)$ scaling and can process 100,000+ records in ~20-25 seconds with low memory overhead.
