export const TRAIN_IMAGE_MAP: Record<string, string> = {
  AVE: "/trenes/s112.webp",
  AVANT: "/trenes/s121.webp",
  MD: "/trenes/s449.webp",
  REGIONAL: "/trenes/s449.webp",
  CERCANIAS: "/trenes/civia.webp",
};

export const TRAIN_TYPE_LABELS: Record<string, string> = {
  AVE: "AVE / Alta Velocidad",
  AVANT: "AVANT / Media Distancia",
  MD: "MD / Media Distancia",
  REGIONAL: "Regional",
  CERCANIAS: "Cercanias",
};

export function getTrainType(trainName?: string): string {
  if (!trainName) return "REGIONAL";
  const type = trainName.trim().split(/\s+/)[0]?.toUpperCase() ?? "REGIONAL";
  return TRAIN_IMAGE_MAP[type] ? type : "REGIONAL";
}

export function getTrainImage(trainName?: string): string {
  const type = getTrainType(trainName);
  return TRAIN_IMAGE_MAP[type] ?? TRAIN_IMAGE_MAP.REGIONAL;
}
