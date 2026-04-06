// One representative image per train type (main photo for cards/modals).
// When you add real .webp photos, name them exactly like the .fake placeholders
// and place them in public/trenes/{type}/. Update the paths below accordingly.
export const TRAIN_IMAGE_MAP: Record<string, string> = {
  AVE:       "/trenes/ave/s112.webp",
  AVLO:      "/trenes/avlo/s106.webp",
  ALVIA:     "/trenes/alvia/s120.webp",
  AVANT:     "/trenes/avant/s114.webp",
  MD:        "/trenes/md/s449.webp",
  REGIONAL:  "/trenes/regional/s596.webp",
  LD:        "/trenes/ld/s252.webp",
  CERCANIAS: "/trenes/cercanias/s447.webp",
};

// All photos available for a given type (for galleries).
export const TRAIN_PHOTOS_MAP: Record<string, string[]> = {
  AVE:       ["/trenes/ave/s100.webp", "/trenes/ave/s102.webp", "/trenes/ave/s103.webp", "/trenes/ave/s112.webp"],
  AVLO:      ["/trenes/avlo/s106.webp"],
  ALVIA:     ["/trenes/alvia/s120.webp", "/trenes/alvia/s121.webp", "/trenes/alvia/s130.webp"],
  AVANT:     ["/trenes/avant/s104.webp", "/trenes/avant/s114.webp"],
  MD:        ["/trenes/md/s449.webp", "/trenes/md/s450.webp", "/trenes/md/s592.webp", "/trenes/md/s594.webp", "/trenes/md/s598.webp"],
  REGIONAL:  ["/trenes/regional/s592.webp", "/trenes/regional/s596.webp", "/trenes/regional/s598.webp"],
  LD:        ["/trenes/ld/s252.webp", "/trenes/ld/s730.webp", "/trenes/ld/s269.webp"],
  CERCANIAS: ["/trenes/cercanias/s440.webp", "/trenes/cercanias/s446.webp", "/trenes/cercanias/s447.webp", "/trenes/cercanias/s448.webp", "/trenes/cercanias/s470.webp"],
};

export const TRAIN_TYPE_LABELS: Record<string, string> = {
  AVE:       "Tren de Alta Velocidad",
  AVLO:      "AVLO (Alta Velocidad Low Cost)",
  ALVIA:     "ALVIA (Alta Velocidad + Larga Distancia)",
  AVANT:     "AVANT (AVE Regional)",
  MD:        "Media Distancia",
  REGIONAL:  "Tren Regional",
  LD:        "Larga Distancia",
  CERCANIAS: "Cercanías",
};

// Map from the pipeline's train_type string to the key in maps above
export const TYPE_KEY_MAP: Record<string, string> = {
  "AVE":              "AVE",
  "AVLO":             "AVLO",
  "Alvia":            "ALVIA",
  "Avant":            "AVANT",
  "Media Distancia":  "MD",
  "Regional":         "REGIONAL",
  "Larga Distancia":  "LD",
  "Cercanías":        "CERCANIAS",
};

export function getTrainTypeKey(trainType: string | undefined): string {
  if (!trainType) return "REGIONAL";
  return TYPE_KEY_MAP[trainType] ?? "REGIONAL";
}

export function getTrainType(trainName: string | undefined): string {
  if (!trainName) return "REGIONAL";
  const type = trainName.trim().split(/\s+/)[0]?.toUpperCase() ?? "REGIONAL";
  return type in TRAIN_IMAGE_MAP ? type : "REGIONAL";
}

export function getTrainImage(trainName: string | undefined): string {
  return TRAIN_IMAGE_MAP[getTrainType(trainName)] || TRAIN_IMAGE_MAP.REGIONAL;
}
