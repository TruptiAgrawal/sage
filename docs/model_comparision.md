# Model Comparison: Random Forest vs CatBoost vs LightGBM

## Objective

The objective of this analysis is to compare three regression models used for predicting:

- Input Tokens
- Output Tokens
- API Cost

These models are evaluated based on prediction accuracy, training strategy, speed, and overall performance.

---

## 1. Random Forest Regression

### Overview
Random Forest is an ensemble learning algorithm that builds multiple decision trees and combines their predictions by averaging the outputs.

### Advantages
- Easy to understand and implement
- Reduces overfitting
- Good baseline model
- Performs well on structured data

### Disadvantages
- Slower prediction with many trees
- Does not learn from previous tree errors

---

## 2. CatBoost Regression

### Overview
CatBoost is a gradient boosting algorithm that builds trees sequentially, where each new tree corrects the errors made by previous trees.

### Advantages
- Excellent accuracy
- Handles categorical features efficiently
- Reduces overfitting
- Strong performance on tabular datasets

### Disadvantages
- Longer training time than Random Forest
- More hyperparameters to tune

---

## 3. LightGBM Regression

### Overview
LightGBM is a gradient boosting framework that grows trees using a leaf-wise strategy for faster training.

### Advantages
- Fast training
- Low memory usage
- Scales well for large datasets

### Disadvantages
- Can overfit on small datasets
- Requires careful parameter tuning

# Conclusion

Among the three regression models, CatBoost provides the best overall performance for token prediction. It achieves the highest prediction accuracy for both input and output tokens, leading to more reliable API cost estimation. Random Forest serves as a strong baseline model, while LightGBM offers faster training but slightly lower prediction accuracy on this dataset.