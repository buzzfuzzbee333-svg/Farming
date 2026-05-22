import { Platform } from "react-native";

export const colors = {
  bg: "#09090b", // zinc-950
  surface: "#18181b", // zinc-900
  surface2: "#0A0A0A",
  surfaceDeep: "#050505",
  border: "rgba(255,255,255,0.10)",
  borderStrong: "rgba(255,255,255,0.18)",
  text: "#fafafa",
  textSecondary: "#a1a1aa", // zinc-400
  textTertiary: "#52525b", // zinc-600
  accent: "#22c55e", // green-500
  accentSoft: "rgba(34,197,94,0.10)",
  accentBorder: "rgba(34,197,94,0.35)",
  blue: "#60a5fa",
  blueSoft: "rgba(96,165,250,0.10)",
  blueBorder: "rgba(96,165,250,0.35)",
  red: "#f87171",
  redSoft: "rgba(248,113,113,0.10)",
  redBorder: "rgba(248,113,113,0.35)",
  yellow: "#facc15",
  zincBadge: "rgba(161,161,170,0.12)",
  zincBadgeBorder: "rgba(161,161,170,0.35)",
};

export const mono = Platform.select({
  ios: "Menlo",
  android: "monospace",
  default: "monospace",
}) as string;

export const sans = Platform.select({
  ios: "System",
  android: "Roboto",
  default: "System",
}) as string;

export const radius = {
  sm: 3,
  md: 4,
};

export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
};

export function statusStyle(status: string) {
  switch (status) {
    case "running":
      return {
        bg: colors.accentSoft,
        border: colors.accentBorder,
        fg: colors.accent,
      };
    case "completed":
      return { bg: colors.blueSoft, border: colors.blueBorder, fg: colors.blue };
    case "failed":
      return { bg: colors.redSoft, border: colors.redBorder, fg: colors.red };
    default:
      return {
        bg: colors.zincBadge,
        border: colors.zincBadgeBorder,
        fg: colors.textSecondary,
      };
  }
}

export function formatUSD(cents: number) {
  return `$${(cents / 100).toFixed(2)}`;
}

export function formatMinutes(mins: number) {
  if (mins < 60) return `${mins}m`;
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m === 0 ? `${h}h` : `${h}h ${m}m`;
}
