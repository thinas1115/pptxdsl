# VLAN基礎研修

新入社員がVLANの役割、Access / Trunk、IEEE 802.1Q、VLAN間ルーティング、
SVI・RP・ルーターサブインターフェース、Cisco設定と確認、障害切り分けを順に学ぶ32枚の研修資料です。

- [生成済みPowerPoint](vlan_training.pptx)
- [全36枚プレビュー](preview.png)
- [入力データ](content.json)

この資料では、一般的な構成図だけでは表しにくい技術研修向けの次のtypeを使用しています。

- `network`: 物理機器、論理セグメント、Access / Trunk / L3接続
- `concept`: 用語の定義、要点、誤解しやすい境界
- `protocol_anatomy`: フレーム・パケットのフィールド構造
- `code_lab`: 設定例と実行後の確認観点
- `knowledge_check`: 選択式の設問と正答・解説

## 再生成と検証

リポジトリルートから実行します。

```powershell
python slidegen/validate_content.py examples/training/vlan/content.json
python slidegen/generate_from_json.py examples/training/vlan/content.json examples/training/vlan/vlan_training.pptx
python slidegen/check_layout.py examples/training/vlan/vlan_training.pptx
```

PowerPointを利用できる環境では、実レンダリングも確認します。

```powershell
powershell -ExecutionPolicy Bypass -File render.ps1 `
  -PptxPath examples/training/vlan/vlan_training.pptx `
  -OutDir out/vlan-training-preview
python contact_sheet.py out/vlan-training-preview
```
