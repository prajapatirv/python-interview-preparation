---
id: python-data
title: Data handling: pandas & Airflow
order: 7
summary: pandas at scale, memory, vectorisation; Airflow DAGs, scheduling and idempotent tasks.
docs: python/python-interview-prep/deep_dive/09_pandas.md, python/python-interview-prep/deep_dive/34_airflow_orchestration.md
folders: 03_pandas_data_handling, 14_airflow_orchestration
examples: python/python-interview-prep/14_airflow_orchestration
keywords: pandas, dataframe, numpy, csv, groupby, merge, airflow, dag, operator, xcom, scheduler, backfill, sensor, etl, pipeline, couchbase
---
Skill focus for Data handling: pandas & Airflow answers:
- pandas: vectorise instead of loops, dtypes and memory, chunked reading for large files.
- Airflow: data intervals, idempotent and re-runnable tasks, retries, backfills, sensors vs deferrable operators.
- Tell it as a pipeline that failed at 3 a.m. and how it was made safe to re-run.
