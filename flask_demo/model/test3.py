import torch
from transformers import AutoTokenizer, AutoModelForSequenceClassification

# 加载预训练模型和分词器
model_name = "./ClassificationModel"
tokenizer = AutoTokenizer.from_pretrained('hfl/chinese-bert-wwm')
model = AutoModelForSequenceClassification.from_pretrained(model_name)

# 确保模型在正确的设备上
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

# 准备输入数据
input_text = "我的老伴今天去世了，我好孤单"

# 使用分词器对输入文本进行预处理
inputs = tokenizer(input_text, return_tensors="pt", padding=True, truncation=False).to(device)

# 前向传播
with torch.no_grad():
    outputs = model(**inputs)

# 解析输出
logits = outputs.logits
predicted_class_id = logits.argmax(-1).item()

# 显示预测结果
print(f"预测类别 ID: {predicted_class_id}")