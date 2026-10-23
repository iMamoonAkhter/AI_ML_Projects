# Methodology Flowchart — Mermaid Source

This file contains the Mermaid.js source for the 3-Phase methodology pipeline
(Section 3). Paste the code block below into a Mermaid renderer (e.g.,
https://mermaid.live), export as PNG/SVG, and insert the image into your Word
document. Many Markdown editors and the Mermaid Live Editor render it directly.

```mermaid
flowchart TD
    A["Data Input<br/>Global Fuel Prices, 2020–2026<br/>84 Countries · Weekly Series"]

    subgraph P1["Phase I — Data Preprocessing"]
        direction TB
        B["Chronological Train/Test Split<br/>(leakage prevention)"]
        C["Lag-1 Shifting of Predictors"]
        D["Standardization<br/>(fitted on training partition)"]
        B --> C --> D
    end

    subgraph P2["Phase II — Unsupervised Learning (EWS)"]
        direction TB
        E["Feature Engineering<br/>Cross-Commodity Ratio · Brent Momentum"]
        F["K-Means Clustering<br/>K = 4"]
        G["Four Market Regimes<br/>Normal · Local Peak · Global Inflation · Severe Crisis"]
        E --> F --> G
    end

    subgraph P3["Phase III — Supervised Learning"]
        direction TB
        H["Model Inputs<br/>Lagged Features + EWS Regime Labels + Temporal Codes"]
        I["Forecasting Models<br/>Linear Regression · KNN · Random Forest · XGBoost"]
        J["Output<br/>Fuel Price Forecast"]
        H --> I --> J
    end

    A --> B
    D --> E
    G --> H

    classDef input fill:#1F3864,stroke:#10233F,stroke-width:1px,color:#FFFFFF;
    classDef p1 fill:#EAF1F8,stroke:#2E5C9A,stroke-width:1px,color:#1A1A1A;
    classDef p2 fill:#E9F5EE,stroke:#2E8B57,stroke-width:1px,color:#1A1A1A;
    classDef p3 fill:#FBEFE3,stroke:#C9772F,stroke-width:1px,color:#1A1A1A;
    classDef output fill:#1F3864,stroke:#10233F,stroke-width:1px,color:#FFFFFF;

    class A input;
    class B,C,D p1;
    class E,F,G p2;
    class H,I,J p3;
    class J output;

    style P1 fill:#F7FAFD,stroke:#2E5C9A,stroke-width:1.5px,color:#1F3864;
    style P2 fill:#F6FBF8,stroke:#2E8B57,stroke-width:1.5px,color:#1F5C3A;
    style P3 fill:#FDF8F2,stroke:#C9772F,stroke-width:1.5px,color:#8A4E18;
```
