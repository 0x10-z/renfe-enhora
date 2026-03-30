// Train type to image mapping
export const TRAIN_IMAGE_MAP: Record<string, string> = {
  AVE: "/trenes/s112.webp",
  AVANT: "/trenes/s121.webp",
  MD: "/trenes/s449.webp",
  REGIONAL: "/trenes/s449.webp",
  CERCANIAS: "/trenes/civia.webp",
};

/**
 * Extract train type from train_name (e.g., "AVE 12345" → "AVE")
 */
export function extractTrainType(trainName: string | undefined): string {
  if (!trainName) return "REGIONAL";
  const parts = trainName.trim().split(/\s+/);
  const type = parts[0]?.toUpperCase() ?? "REGIONAL";
  return type in TRAIN_IMAGE_MAP ? type : "REGIONAL";
}

/**
 * Get the image path for a train type
 */
export function getTrainImage(trainName: string | undefined): string {
  const type = extractTrainType(trainName);
  return TRAIN_IMAGE_MAP[type] || TRAIN_IMAGE_MAP.REGIONAL;
}

/**
 * Get a friendly name for the train type
 */
export function getTrainTypeLabel(trainName: string | undefined): string {
  const type = extractTrainType(trainName);
  const labels: Record<string, string> = {
    AVE: "Tren de Alta Velocidad",
    AVANT: "AVANT (Media Distancia)",
    MD: "Media Distancia",
    REGIONAL: "Tren Regional",
    CERCANIAS: "Cercanías",
  };
  return labels[type] || "Tren";
}
