# dbapi-mongodb コンセプト

Python から MongoDB を SQL 風に扱うための DBAPI ライブラリ。`pymongo` に依存し、SQL 文を Mongo クエリへ変換して返すことで、既存の RDB アプリケーション移行を支援する。

## 想定ユーザーと課題
- Python で DBAPI 互換のコードを書いており、MongoDB への置き換えでも既存の SQL 呼び出しを大きく変えたくない開発者。
- MongoDB のクエリ構文に不慣れでも、SQL 文で CRUD を行いたいチーム。
- クエリ変換時のエラーメッセージと挙動を明確にし、運用で混乱したくない担当者。

## ユースケース/機能一覧
| Spec ID | 機能 | 詳細 | 依存 | フェーズ |
| --- | --- | --- | --- | --- |
| F1 | DBAPI 接続生成 | `connect()` で MongoDB クライアント/データベースを初期化し、接続情報は URI/DB 名で指定。| `pymongo.MongoClient` | MVP |
| F2 | SQL→Mongo 変換 (SELECT) | `cursor.execute()` で SELECT を受け取り、`find`/`find_one` を組み立てて結果を返す。 | F1 | MVP |
| F3 | SQL→Mongo 変換 (INSERT/UPDATE/DELETE) | DML を `insert_one`/`update_many`/`delete_many` に変換。| F1 | MVP |
| F4 | パラメータバインド | `execute(sql, params)` でプレースホルダーを Mongo フィルタ/値に安全適用。 | F2, F3 | MVP |
| F5 | 例外/エラー整理 | SQL 解析失敗や未対応構文を Error ID 付き例外にマップ。 | F2, F3 | MVP |
| F6 | トランザクション/セッション | `begin`/`commit`/`rollback` 互換 API で MongoDB セッション/トランザクションをラップ。 | F1 | Phase2 |
| F7 | メタデータ取得 | コレクション一覧や簡易スキーマ情報を DBAPI ライクなメソッドで取得。 | F1 | Phase2 |
| F8 | JOIN/集計拡張 | INNER/LEFT JOIN（等価結合）、`OR`/`LIKE`/`BETWEEN`、`GROUP BY` など RDB 互換を強化。 | F2 | Phase2 |
| F9 | DDL/インデックス | `CREATE/DROP TABLE`（コレクション作成/削除）、`CREATE/DROP INDEX` をサポート。 | F1 | Phase2 |
| F10 | SQLAlchemy 対応 | DBAPI モジュール属性と dialect を提供し、SQLAlchemy から利用可能にする。 | F1〜F9 | Phase3 |
| F11 | 高度な SQL 対応 | サブクエリ、UNION、HAVING、非等価/多段 JOIN、ウィンドウ関数、ILIKE/正規表現リテラル、名前付きパラメータ対応。 | F2, F8 | Phase4 |
| F12 | 型対応拡張 | Decimal/UUID/タイムゾーン付き datetime 等の型変換ポリシー明確化と実装。 | F2 | Phase4 |
| F13 | JOIN 投影/alias 強化 | JOIN 先の列をそのまま/別名で投影可能にし、JOIN + WHERE/HAVING で alias 解決を安定化。 | F8 | Phase5 |
| F14 | CASE を含む集計 | `SUM(CASE WHEN ... THEN ... ELSE ... END)` など簡易な条件付き集計を `$cond` でサポート。 | F8 | Phase5 |
| F15 | HAVING で集計 alias | `HAVING SUM(total) >= 100` など集計 alias を HAVING で解決できるようにする。 | F8 | Phase5 |
| F16 | ウィンドウ関数拡張 | `ROW_NUMBER()` を基点に、基本的なウィンドウ関数サポートを拡張する（MongoDB 5+ 前提）。 | F11 | Phase6 |

## 機能詳細メモ
- MVP では CRUD とパラメータバインドを優先し、SQL パーサーは限定構文（簡易 WHERE, LIMIT, ORDER BY）に絞る。
- DDL は最小限（CREATE TABLE → コレクション作成、DROP TABLE → コレクション削除、CREATE/DROP INDEX）をサポートし、インデックスは複合・UNIQUE を許容する。
- JOIN は INNER/LEFT の等価結合（複合キー含む、2 段まで）をサポートし、それ以外は未対応エラーで扱う。将来的に SQLAlchemy 方言での利用を想定。
- WHERE は `OR`、`LIKE`（%/ _ を `$regex` に変換）、`BETWEEN` を追加対応し、集計 (`GROUP BY` + 集約関数) を `$group` にマッピングする。
- トランザクションは 3.6 など未対応環境では no-op で成功扱いとし、4.x 以降でセッションを張る。
- パラメータバインドは `%s` と `%(name)s` を受け付け、dict/sequence で適用する（不足/余剰はエラー）。
- 拡張機能（P1→P4 の順）:  
  - P1: SQLAlchemy Core 強化（Table/Column CRUD/DDL/Index を実通信で通すため、サブクエリ/UNION ALL/HAVING/多段 JOIN/ILIKE・正規表現リテラル、名前付きパラメータ、型拡張を揃える）  
  - P2: ORM 最小 CRUD（単一テーブル相当、PK→`_id` マッピング、P1 の型/パラメータを流用）  
  - P3: async dialect（Core CRUD/DDL/Index を async 化、トランザクション方針は同じ）  
  - P4: Mongo 5+ 前提のウィンドウ関数対応（`ROW_NUMBER` など）
  - P5: JOIN 投影/alias 強化、CASE 集計、HAVING 集計 alias 対応（SQL 移植時の詰まりポイント解消）
  - P6: ウィンドウ関数拡張（ROW_NUMBER 以外の基本関数の検討）
- トランザクションは MongoDB のレプリカセット/トランザクション対応クラスタを前提（Phase2）。
- MongoDB のバージョン/構成でトランザクションが未サポートの場合は実行前に検出し、明示的にエラー返却する。
- SQL サポート範囲（現状）: `SELECT/INSERT/UPDATE/DELETE`、`CREATE/DROP TABLE`、`CREATE/DROP INDEX`、`WHERE`（比較/`AND`/`OR`/`IN`/`BETWEEN`/`LIKE`）、`ORDER BY`、`LIMIT/OFFSET`、INNER/LEFT 等価 JOIN（複合キー/2 段）、`GROUP BY` + 集計、`UNION ALL`、`HAVING`。
- 将来拡張: SQLGlot を採用することでサブクエリやより複雑な構文にも対応する余地を残す（Phase2 以降で検討）。

## 使用するライブラリ
- `pymongo`: MongoDB 公式ドライバ。接続と CRUD/セッションを提供。
- `SQLGlot`: AST を取得して方言差分やサブクエリ対応を見据えたパーサーとして採用する。

## ソフトウェア全体設計の概要
- DBAPI 互換の接続オブジェクト/カーソルオブジェクトを公開し、SQL 文字列の受付口を DBAPI に寄せる。
- SQL 解析→Mongo クエリ生成→`pymongo` 実行→結果正規化（タプル行）というパイプライン構造。
- エラーメッセージは Error ID 付きで一元管理し、テストで文字列一致を担保する。
