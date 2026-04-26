/**
 * Tech Stack Constants
 * 
 * Single source of truth for all technology skills in the portfolio.
 * Images are resolved from /public/tech/ or /public/icons/ directories.
 * 
 * To add a new skill:
 * 1. Place the image in /public/tech/<skill-name>.svg (or .png, .jpg)
 * 2. Add an entry to TECH_STACK below
 * 3. If image doesn't exist, fallback will show a gradient placeholder
 */

export type TechItem = {
  name: string;
  category?: 'frontend' | 'backend' | 'fullstack' | 'language' | 'tool' | 'design';
};

// Helper function to normalize skill names (case-insensitive)
const normalizeName = (name: string): string => {
  return name.toLowerCase().trim().replace(/\s+/g, ' ');
};

// Helper function to resolve logo path
// Checks /public/tech/ first, then /public/icons/, then fallback
export const getLogoForSkill = (name: string, fallbackPath?: string): string => {
  // If fallback path is provided, use it
  if (fallbackPath) return fallbackPath;
  
  // Try /tech/ directory first
  const techPath = `/tech/${name.toLowerCase().replace(/\s+/g, '-')}.svg`;
  
  // For now, we'll use the mapping logic in the component
  // This function can be enhanced to actually check file existence
  return techPath;
};

// Tech stack array - use directly, no merging or deduplication
export const TECH_STACK: TechItem[] = [
  { name: 'AWS'},
  { name: 'Google Cloud Platform'},
  { name: 'Next.js'},
  { name: 'React JS'},
  { name: "Git"},
  { name: 'Github'},
  { name: "Hono"},
  { name: 'TypeScript'},
  { name: 'Express.js'},
  { name: 'JavaScript'},
  { name: 'MongoDB'},
  { name: 'Socket.IO'},
  { name: 'SWR'},
  { name: 'Vercel'},
  { name: 'Tailwind CSS'},
  { name: 'Zustand'},
  { name: 'Nodemailer'},
  { name: 'Prisma'},
  { name: 'MySQL'},
  { name: 'PostgreSQL'},
  { name: 'Docker'},
  { name: 'React Native'},
  { name: 'HTML 5'},
  { name: 'CSS'},
  { name: 'React'},
  { name: 'Framer Motion'},
  { name: 'Python'},
  { name: 'Streamlit'},
  { name: 'scikit-learn'},
  { name: 'LangGraph'},
  { name: 'FAISS'},
  { name: 'Groq'},
  { name: 'C++'},
  { name: 'Java'},
  { name: 'Figma'},
  { name: 'Node.js'},
  { name: 'Firebase'},
  { name: 'Expo'},
  { name: 'Expo Orbit'},
  { name: 'Notion'},
  { name: 'Test Flight'},
  { name: 'Markdown'},
  { name: 'Jupyter'},
  { name: 'SQL'},
  { name: 'Terminal'},
];

