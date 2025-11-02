"""Small in-game guide renderer for Level 2.

This module provides a single helper `draw_guide_overlay` which draws a
centered semi-opaque panel with concise control instructions. Kept
very small so it can be imported safely.
"""
import pygame

# Lines displayed in the guide (short and clear)
GUIDE_LINES = [
	"Controls:",
	"  - Move: WASD or Arrow keys",
	"  - Aim: Mouse (move cursor)",
	"  - Shoot: Space",
	"  - Launch/Recall Mushroom Ball: R",
	"  - Powerups: click the slot(s) at the bottom (click twice to confirm)",
	"Objective:",
	"  - Hit all the mushroom villains (goals) to clear the level",
	"Press Y to close this guide"
]


def draw_guide_overlay(screen, font, big_font, screen_w, screen_h):
	"""Draw a centered guide overlay.

	Args:
		screen: pygame Surface to draw onto.
		font: small font (pygame.font.Font) for body text.
		big_font: larger font for title.
		screen_w/screen_h: dimensions (ints) of the screen.
	"""
	try:
		pad = 18
		w = min(640, int(screen_w * 0.8))
		line_h = 22
		h = line_h * (len(GUIDE_LINES) + 1) + pad * 2
		gx = (screen_w - w) // 2
		gy = max(40, (screen_h - h) // 3)

		guide_surf = pygame.Surface((w, h), pygame.SRCALPHA)
		guide_surf.fill((12, 12, 12, 220))

		# title
		try:
			title = big_font.render("Short Guide", True, (255, 230, 160))
			guide_surf.blit(title, (pad, pad))
		except Exception:
			pass

		# draw lines
		line_y = pad + 40
		for line in GUIDE_LINES:
			try:
				txt = font.render(line, True, (240, 240, 240))
				guide_surf.blit(txt, (pad, line_y))
			except Exception:
				pass
			line_y += line_h

		# subtle border
		try:
			pygame.draw.rect(guide_surf, (200, 180, 120, 140), guide_surf.get_rect(), 2)
		except Exception:
			pass

		screen.blit(guide_surf, (gx, gy))
	except Exception:
		# Drawing failures should never crash the game
		pass

