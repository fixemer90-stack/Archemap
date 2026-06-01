export function Footer() {
  return (
    <footer className="border-t py-6">
      <div className="container mx-auto flex items-center justify-between px-4 text-sm text-muted-foreground">
        <p>&copy; {new Date().getFullYear()} Astrotype. All rights reserved.</p>
        <nav className="flex gap-4">
          <a href="#" className="hover:text-foreground transition-colors">
            Privacy
          </a>
          <a href="#" className="hover:text-foreground transition-colors">
            Terms
          </a>
          <a href="#" className="hover:text-foreground transition-colors">
            Support
          </a>
        </nav>
      </div>
    </footer>
  );
}
