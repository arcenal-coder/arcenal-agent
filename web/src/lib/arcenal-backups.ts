const ARCHIVE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9_.+-]{0,79}$/;

export function backupArchiveNames(items: Array<Record<string, unknown>>): string[] {
  const names = items.map(archiveName).filter((name) => ARCHIVE_PATTERN.test(name));
  return [...new Set(names)];
}

function archiveName(item: Record<string, unknown>): string {
  const value = item.id ?? item.name;
  return typeof value === "string" ? value : "";
}
