import cv2
import numpy as np
import pygame
import math

colors = { # hsv color limits for red, green, blue
    "red":[((0,120,70),(10,255,255)),((170,120,70),(180,255,255))],
    "green":[((36,50,70),(89,255,255))],
    "blue":[((90,50,70),(128,255,255))]}
rules = {("triangle","red"):"dangerous",
         ("square","blue"):"boundary", 
         ("circle","green"):"safe"}

class Plane:
    def __init__(self, w=600, h=400):  # Fixed: double underscores
        self.w, self.h = w, h
        self.run = True
        self.roll = 0
        self.pitch = 0
        self.txt = ""
        pygame.init()
        self.scr = pygame.display.set_mode((w, h))
        pygame.display.set_caption("Plane Control")  # Added window title
        self.clock = pygame.time.Clock()
        
    def draw(self):
        c = (self.w//2, self.h//2)
        self.scr.fill((20, 20, 40))
        # roll=tilt, pitch=up/down
        ang = math.radians(self.roll * 25)
        dx = int(100 * math.cos(ang))
        dy = int(100 * math.sin(ang))
        off = int(self.pitch * 40)
        # wings
        pygame.draw.line(self.scr, (230, 230, 230), (c[0]-dx, c[1]+dy+off), (c[0]+dx, c[1]-dy+off), 10)
        # body
        pygame.draw.line(self.scr, (200, 200, 200), (c[0], c[1]+80+off), (c[0], c[1]-80+off), 8)
        # tail
        pygame.draw.line(self.scr, (180, 180, 180), (c[0]-40, c[1]+60+off), (c[0]+40, c[1]+60+off), 6)
        pygame.draw.circle(self.scr, (255, 255, 255), (c[0], c[1]+off), 10)
        # text
        f = pygame.font.SysFont("Arial", 18)
        self.scr.blit(f.render(self.txt, 1, (200, 255, 200)), (20, 20))
        pygame.display.flip()
        
        for e in pygame.event.get():
            if e.type == pygame.QUIT or (e.type == pygame.KEYDOWN and e.key == pygame.K_q): 
                self.run = False
        self.clock.tick(60)
        
def main():
    cam = cv2.VideoCapture(0)  # Removed CAP_DSHOW for better compatibility
    if not cam.isOpened(): 
        print("No camera found")
        return
        
    plane = Plane()
    
    while plane.run:
        ok, frame = cam.read()
        if not ok: 
            continue
            
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        objs = []
        
        # detect colors+shapes
        for clr, rngs in colors.items():
            mask = None
            for lo, hi in rngs:
                m = cv2.inRange(hsv, np.array(lo), np.array(hi))
                mask = m if mask is None else cv2.bitwise_or(mask, m)
                
            # Fixed: handle different OpenCV versions
            contours_result = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            if len(contours_result) == 3:
                _, cnts, _ = contours_result
            else:
                cnts, _ = contours_result
                
            for c in cnts:
                if cv2.contourArea(c) < 300: 
                    continue
                peri = cv2.arcLength(c, True)
                poly = cv2.approxPolyDP(c, 0.04 * peri, True)
                shape = "triangle" if len(poly) == 3 else "square" if len(poly) == 4 else "circle"
                lbl = rules.get((shape, clr))
                x, y, w, h = cv2.boundingRect(c)
                objs.append(((x, y, w, h), shape, clr, lbl))
                cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 255), 2)
                cv2.putText(frame, clr + " " + shape, (x, y-5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
                
        # avoidance
        roll = pitch = 0
        msg = "no obj"
        if objs:
            (x, y, w, h), sh, cl, l = max(objs, key=lambda o: o[0][2] * o[0][3])
            cx, cy = x + w//2, y + h//2
            cw, ch = frame.shape[1]//2, frame.shape[0]//2
            if cx < cw - 50: 
                roll = 1
                msg = "left→roll right"
            elif cx > cw + 50: 
                roll = -1
                msg = "right→roll left"
            if cy < ch - 50: 
                pitch = -1
                msg += " top→down"
            elif cy > ch + 50: 
                pitch = 1
                msg += " bottom→up"
                
        plane.roll, plane.pitch, plane.txt = roll, pitch, msg
        plane.draw()
        
        cv2.imshow("detect", frame)
        if cv2.getWindowProperty("detect", cv2.WND_PROP_VISIBLE) < 1: 
            break
        if cv2.waitKey(1) & 0xFF == ord('q'): 
            break
            
    cam.release()
    cv2.destroyAllWindows()
    pygame.quit()
    
if __name__ == "__main__":  # Fixed: proper main check
    main()