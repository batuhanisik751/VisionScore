const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const MAX_SIZE = 20 * 1024 * 1024;

export const ACCEPT_ATTR = "image/jpeg,image/png,image/webp";

/** Check if a file is an accepted image. */
export function isAcceptedImage(file: File): boolean {
  if (file.size > MAX_SIZE) return false;
  return ACCEPTED_TYPES.includes(file.type);
}

/** Create a preview blob URL for an uploaded file. */
export function prepareImage(file: File): { file: File; previewUrl: string } {
  return { file, previewUrl: URL.createObjectURL(file) };
}
