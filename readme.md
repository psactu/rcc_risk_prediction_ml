# RCC Risk Prediction ML

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

This repository contains a survival analysis pipeline for machine learning model development and validation using Monte Carlo Cross-Validation (MCCV) with 100 simulations. External validation of the model is also included.
The goal is to develop a pre-operative (T0) prognostic model for Renal Cell Carcinoma (RCC), with cancer-specific mortality (CSM) as the endpoint.

## License

This project is licensed under the [MIT License](LICENSE).

## Execution Environment

Execution of the pipeline is tied to **Azure Machine Learning**, leveraging Azure data assets for data management and Azure compute clusters for job execution. The analysis scripts and notebooks are built on open-source Python libraries (e.g., `scikit-survival`, `lifelines`, `shap`).

## Project Structure

The notebooks and scripts are designed to be **run in sequence** based on their numerical prefix (00, 01, 02, etc.). Each step builds upon the previous ones.

### Execution Order

#### 01 - Exploratory Data Analysis
- **Goal**: Understand data distribution, patterns, and relationships
- `01_eda_raw.ipynb` - EDA and Kaplan-Meier curves on the pre-processed dataset

#### 02 - Survival Model Fine-tuning (GRANT Features)
- **Goal**: Fine-tune Cox models using GRANT features as baseline with comprehensive validation
- Uses MCCV with 100 simulations via papermill orchestration
- `02_survival_grant_finetune_*.ipynb` - Core fine-tuning notebooks
- `02_monte_carlo_orchestrator.ipynb` - Orchestrator for MCCV simulations using papermill
- `02_monte_carlo_collector.ipynb` - Collects metrics from all MCCV simulations

#### 03 - Feature Selection
- **Goal**: Perform feature selection using Random Survival Forest and analyze feature importance (permutation importance)
- Uses MCCV with 100 simulations via papermill orchestration
- `03_survival_feature_selection_*.ipynb` - Feature selection notebooks
- `03_monte_carlo_orchestrator.ipynb` - Orchestrator for MCCV simulations using papermill
- `03_monte_carlo_collector.ipynb` - Collects importance metrics

#### 04 - Survival Models Training
- **Goal**: Train and validate various survival models with selected features
- Uses cluster-based parallel execution for computationally intensive models
- `04_survival_models_raw_csm.py` - Core training script
- `04_monte_carlo_orchestrator_cluster.ipynb` - Orchestrator for MCCV simulations using Azure cluster
- `04_monte_carlo_collector.ipynb` - Collects model performance metrics

#### 05 - Model Comparison
- **Goal**: Compare performance of all trained models (internal validation)
- `05_compare_models.ipynb` - Comprehensive model comparison over the MCCV simulations, and selection of the best model

#### 06 - Final Model Training
- **Goal**: Train best performing model on full (internal) dataset
- `06_train_full_dataset.ipynb` - Train final model on 100% of internal data

#### 07 - Explainable AI (XAI)
- **Goal**: Generate model interpretability analysis
- `07_xai.ipynb` - Feature importance, SHAP values, and model explanation

#### 08 - External Validation
- **Goal**: Validate final model on external dataset with risk stratification
- `08_external_validation_risk_stratification.ipynb` - Bootstrap validation and Kaplan-Meier curves for the risk groups

### Validation Methodology

The project employs **Monte Carlo Cross-Validation (MCCV) with 100 simulations** for robust internal validation:

- **Low-training models**: Use `papermill` to execute notebooks with different random seeds
- **Computationally intensive models**: Use cluster-based parallel execution
- **Architecture**:c
  - **Orchestrator**: Injects random seeds into notebooks/scripts and manages parallel execution
  - **Collector**: Aggregates metrics from all experiments for analysis and comparison

Ref. Chapter 8.5.2 from https://www.ncbi.nlm.nih.gov/books/NBK543527/pdf/Bookshelf_NBK543527.pdf

### Key Directories

- `artifacts/` - Stored model metrics and results
- `papermill/` - Papermill-generated notebook executions
- `figures/` - Generated plots and visualizations
- `src/` - Source code and utility functions

### Environment

- `env/requirements.txt` - Python package dependencies
- `env/export_env.py` - Utility script to export the current environment
- Utility functions: `04_survival_models/src/uc2_functions.py`
