# 📦 Fake-Compression-fcreader
用于读取Fake-Compression打包产生的`.fckey`密钥内容

## 🧠 工作原理
- 🔑经过验证的元数据存储在与终端同名的外部.fckeysidecar文件中。
- 🗂️ 完成校验后自动读出原文。

## 🔄恢复流程
fcreader压缩将执行以下操作：
- 📖 读取后续的.fckeysidecar 文件
- 🔓 解密并验证元数据
- 👁️ 将得到的原文提交到面板，并提供复制入口，用于用户自行解压

## 📝文件命名与兼容性
- 外部包文件名不是标识字段
- 有且只有`Fake-Compression`和`fcreader`读取且自动关联文件后缀

🚀 从源代码运行
