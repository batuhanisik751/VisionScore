import heic2any from "heic2any";

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/heic", "image/heif"];
const HEIC_EXTENSIONS = [".heic", ".heif"];
const ACCEPT_ATTR = "image/jpeg,image/png,image/webp,image/heic,image/heif,.heic,.heif";
const MAX_SIZE = 20 * 1024 * 1024;

function getExtension(name: string): string {
  const dot = name.lastIndexOf(".");
  return dot >= 0 ? name.slice(dot).toLowerCase() : "";
}

function isHeic(file: File): boolean {
  return (
    file.type === "image/heic" ||
    file.type === "image/heif" ||
    HEIC_EXTENSIONS.includes(getExtension(file.name))
  );
}

/** Check if a file is an accepted image (by MIME type or extension). */
export function isAcceptedImage(file: File): boolean {
  if (file.size > MAX_SIZE) return false;
  if (ACCEPTED_TYPES.includes(file.type)) return true;
  // Browsers often report empty type for HEIC
  const ext = getExtension(file.name);
  return HEIC_EXTENSIONS.includes(ext);
}

/** Create a preview URL for any accepted image. Converts HEIC to JPEG blob. */
export async function createPreviewUrl(file: File): Promise<string> {
  if (isHeic(file)) {
    const blob = await heic2any({ blob: file, toType: "image/jpeg", quality: 0.8 });
    const result = Array.isArray(blob) ? blob[0] : blob;
    return URL.createObjectURL(result);
  }
  return URL.createObjectURL(file);
}

export { ACCEPT_ATTR };
