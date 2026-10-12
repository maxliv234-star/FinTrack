"""Prevent SwiftData migration failures from erasing user finance data.

Applies only to the pinned Mint Leaf v4.2 migration implementation.
Unknown layouts fail closed during patching; previous changes are idempotent.
"""
from pathlib import Path

DANGEROUS_FALLBACK = '''        } catch {
            // Migration failed — back up the store before resetting
            let storeURL = config.url
            let backupURL = storeURL.deletingLastPathComponent()
                .appendingPathComponent("MintLeaf-backup-\(Int(Date().timeIntervalSince1970)).store")
            try? FileManager.default.copyItem(at: storeURL, to: backupURL)

            let related = [
                storeURL,
                storeURL.appendingPathExtension("shm"),
                storeURL.appendingPathExtension("wal"),
            ]
            for url in related {
                try? FileManager.default.removeItem(at: url)
            }
            do {
                container = try ModelContainer(for: schema, configurations: [config])
                print("⚠️ SwiftData store was reset due to migration error. Backup saved to \(backupURL.path)")
            } catch {
                fatalError("Failed to configure SwiftData after reset: \(error)")
            }
        }'''

SAFE_FALLBACK = '''        } catch {
            // FINTRACK DATA SAFETY: keep the original financial store intact.
            // Copying only the main SQLite file can omit uncheckpointed WAL data.
            // Stop launch rather than silently starting with an empty database.
            fatalError("FinTrack Mac: не удалось открыть финансовую базу. " +
                       "Автоматический сброс отключён для защиты данных. \(error)")
        }'''


def transform(src: str) -> str:
    if src.count(SAFE_FALLBACK) == 1 and DANGEROUS_FALLBACK not in src:
        return src
    if src.count(DANGEROUS_FALLBACK) != 1 or SAFE_FALLBACK in src:
        raise RuntimeError(
            "Unknown SwiftData migration implementation; refusing unsafe rewrite"
        )
    return src.replace(DANGEROUS_FALLBACK, SAFE_FALLBACK, 1)


def patch(root: Path, rewrite):
    path = root / "MintLeaf/MintLeafApp.swift"
    if not path.is_file():
        raise RuntimeError("Missing MintLeafApp.swift; refusing unsafe patch")
    return rewrite(path, transform)
