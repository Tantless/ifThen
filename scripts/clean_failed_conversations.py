#!/usr/bin/env python
"""
清理数据库中失败或未完成的会话数据

清理规则：
1. 状态为 'failed' 的会话
2. 状态为 'analyzing' 但没有消息的会话
"""
import sqlite3
from pathlib import Path
import os


def get_db_path() -> Path:
    """获取数据库路径"""
    data_dir = os.environ.get("IF_THEN_DATA_DIR", ".data")
    return Path(data_dir) / "db" / "if_then_mvp.sqlite3"


def clean_failed_conversations(dry_run: bool = True):
    """清理失败的会话及其相关数据"""
    db_path = get_db_path()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 查找需要清理的会话
    cursor.execute("""
        SELECT id, title, status, created_at,
               (SELECT COUNT(*) FROM messages WHERE conversation_id = conversations.id) as msg_count
        FROM conversations
        WHERE status = 'failed' OR (status = 'analyzing' AND id NOT IN (SELECT DISTINCT conversation_id FROM messages))
        ORDER BY id
    """)
    conversations_to_delete = cursor.fetchall()

    if not conversations_to_delete:
        print("✓ 没有需要清理的会话")
        conn.close()
        return

    print(f"找到 {len(conversations_to_delete)} 个需要清理的会话：")
    for conv in conversations_to_delete:
        print(f"  - 会话 {conv[0]}: {conv[1]} (状态: {conv[2]}, 消息数: {conv[4]}, 创建时间: {conv[3]})")

    if dry_run:
        print("\n[DRY RUN] 以上会话将被删除（使用 --execute 执行实际删除）")
        conn.close()
        return

    # 执行删除
    conv_ids = [conv[0] for conv in conversations_to_delete]

    print("\n开始清理...")

    # 删除相关的推演数据
    cursor.execute(f"DELETE FROM simulation_turns WHERE simulation_id IN (SELECT id FROM simulations WHERE conversation_id IN ({','.join('?' * len(conv_ids))}))", conv_ids)
    deleted_turns = cursor.rowcount
    print(f"  - 删除 {deleted_turns} 条推演轮次记录")

    cursor.execute(f"DELETE FROM simulations WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_sims = cursor.rowcount
    print(f"  - 删除 {deleted_sims} 条推演记录")

    # 删除分析数据
    cursor.execute(f"DELETE FROM topic_links WHERE topic_id IN (SELECT id FROM topics WHERE conversation_id IN ({','.join('?' * len(conv_ids))}))", conv_ids)
    deleted_topic_links = cursor.rowcount
    print(f"  - 删除 {deleted_topic_links} 条话题链接")

    cursor.execute(f"DELETE FROM segment_summaries WHERE segment_id IN (SELECT id FROM segments WHERE conversation_id IN ({','.join('?' * len(conv_ids))}))", conv_ids)
    deleted_summaries = cursor.rowcount
    print(f"  - 删除 {deleted_summaries} 条分段摘要")

    cursor.execute(f"DELETE FROM relationship_snapshots WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_snapshots = cursor.rowcount
    print(f"  - 删除 {deleted_snapshots} 条关系快照")

    cursor.execute(f"DELETE FROM persona_profiles WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_personas = cursor.rowcount
    print(f"  - 删除 {deleted_personas} 条人格档案")

    cursor.execute(f"DELETE FROM topics WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_topics = cursor.rowcount
    print(f"  - 删除 {deleted_topics} 条话题")

    cursor.execute(f"DELETE FROM segments WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_segments = cursor.rowcount
    print(f"  - 删除 {deleted_segments} 条分段")

    cursor.execute(f"DELETE FROM messages WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_messages = cursor.rowcount
    print(f"  - 删除 {deleted_messages} 条消息")

    cursor.execute(f"DELETE FROM analysis_jobs WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_jobs = cursor.rowcount
    print(f"  - 删除 {deleted_jobs} 条分析任务")

    # 获取导入文件路径用于删除
    cursor.execute(f"SELECT source_file_path FROM imports WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    import_files = [row[0] for row in cursor.fetchall()]

    cursor.execute(f"DELETE FROM imports WHERE conversation_id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_imports = cursor.rowcount
    print(f"  - 删除 {deleted_imports} 条导入记录")

    # 删除会话
    cursor.execute(f"DELETE FROM conversations WHERE id IN ({','.join('?' * len(conv_ids))})", conv_ids)
    deleted_convs = cursor.rowcount
    print(f"  - 删除 {deleted_convs} 个会话")

    # 提交事务
    conn.commit()

    # 删除导入文件
    deleted_files = 0
    for file_path in import_files:
        if file_path and Path(file_path).exists():
            try:
                Path(file_path).unlink()
                deleted_files += 1
            except Exception as e:
                print(f"  ! 无法删除文件 {file_path}: {e}")

    if deleted_files > 0:
        print(f"  - 删除 {deleted_files} 个导入文件")

    print(f"\n✓ 清理完成！共删除 {len(conv_ids)} 个会话及其相关数据")

    conn.close()


if __name__ == "__main__":
    import sys

    dry_run = "--execute" not in sys.argv

    if dry_run:
        print("=== 数据库清理预览（DRY RUN）===\n")
    else:
        print("=== 执行数据库清理 ===\n")

    clean_failed_conversations(dry_run=dry_run)
