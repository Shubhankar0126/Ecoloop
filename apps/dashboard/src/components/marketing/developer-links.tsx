import { developerProfile, type DeveloperLink } from "@/content/site";
import { Button } from "@/components/ui/button";

type DeveloperLinksProps = {
  mode?: "buttons" | "icons";
};

export function DeveloperLinks({ mode = "buttons" }: DeveloperLinksProps) {
  const configuredLinks = developerProfile.links.filter(
    (link): link is DeveloperLink & { href: string } => link.href !== null
  );

  if (configuredLinks.length === 0) {
    return null;
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      {configuredLinks.map((link) => (
        <Button
          key={link.label}
          asChild
          size={mode === "icons" ? "icon" : "default"}
          variant="secondary"
          className={mode === "buttons" ? "justify-start" : undefined}
        >
          <a href={link.href} target="_blank" rel="noreferrer" aria-label={link.label}>
            <link.icon className="h-4 w-4" />
            {mode === "buttons" ? link.label : null}
          </a>
        </Button>
      ))}
    </div>
  );
}
