import {
  PenLine,
  NotebookPen,
  Backpack,
  GraduationCap,
  Puzzle,
  Palette,
  BriefcaseBusiness,
  Printer,
  Ruler,
  FlaskConical,
  BookOpen,
} from 'lucide-react';
const icons = {
  pen: PenLine,
  notebook: NotebookPen,
  backpack: Backpack,
  graduation: GraduationCap,
  puzzle: Puzzle,
  palette: Palette,
  briefcase: BriefcaseBusiness,
  printer: Printer,
  ruler: Ruler,
  flask: FlaskConical,
  book: BookOpen,
};
export function CategoryIcon({ name, size = 24 }: { name: string; size?: number }) {
  const Icon = icons[name as keyof typeof icons] ?? BookOpen;
  return <Icon size={size} strokeWidth={1.5} aria-hidden="true" />;
}
