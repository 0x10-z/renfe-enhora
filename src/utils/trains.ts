export const TRAIN_IMAGE_MAP: Record<string, string> = {
  AVE: "/trenes/s112.webp",
  AVANT: "/trenes/s114.webp",
  ALVIA: "/trenes/s120.webp",
  AVLO: "/trenes/s106.webp",
  MD: "/trenes/s449.webp",
  REGIONAL: "/trenes/s449.webp",
  CERCANIAS: "/trenes/civia.webp",
};

export const TRAIN_TYPE_LABELS: Record<string, string> = {
  AVE: "Tren de Alta Velocidad",
  AVANT: "AVANT (Media Distancia)",
  ALVIA: "ALVIA (Larga Distancia)",
  AVLO: "AVLO (Alta Velocidad)",
  MD: "Media Distancia",
  REGIONAL: "Tren Regional",
  CERCANIAS: "Cercanías",
};

export function getTrainType(trainName: string | undefined): string {
  if (!trainName) return "REGIONAL";
  const type = trainName.trim().split(/\s+/)[0]?.toUpperCase() ?? "REGIONAL";
  return type in TRAIN_IMAGE_MAP ? type : "REGIONAL";
}

export function getTrainImage(trainName: string | undefined): string {
  return TRAIN_IMAGE_MAP[getTrainType(trainName)] || TRAIN_IMAGE_MAP.REGIONAL;
}
