# Code: Terraform 中文译本

本仓库包含《Code: Terraform》玩家文档的中文译本。

## 内容

- `output/pdf/Code_Terraform_中文译本.pdf`：完整中文版 PDF。
- `output/pdf/Code_Terraform_中文译本.md`：可检索、可编辑的合并译稿。
- `build_translated_pdf.py`：生成 PDF 的脚本。

术语在首次出现时采用“中文（English）”形式。示例代码、API 名称、命令、标识符、文件名和字符串字面量均保留英文原样。源文档中的嵌入图示已保留在译本中。

## 复现

将原始 `Code_ Terraform.pdf` 放在仓库根目录后，安装 `pypdf` 与 `reportlab`，运行：

```bash
python3 build_translated_pdf.py
```

源 PDF 未包含在此仓库中。
