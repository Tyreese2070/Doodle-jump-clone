# Importing modules
import os
import random
import time
import pickle
from operator import itemgetter
import pygame

pygame.init()
pygame.mixer.init()

# Creating the window and setting the caption
WIDTH = 400
HEIGHT = 500
SCREEN = pygame.display.set_mode([WIDTH, HEIGHT])
pygame.display.set_caption("Jumping Man")

# Setting the clock and the FPS variable for the main loop
FPS = 60
clock = pygame.time.Clock()

# Game variables
VELOCITY = 7
JUMPFORCE = -17
JUMPHEIGHT = 100
GRAVITY = 0.8
MAX_PLATFORMS = 5
MAX_CLOUDS = 5
CLOUD_VELOCITY = 1
SCROLL_LINE = 150
SCROLL_VELOCITY = 3

# Colours
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BG_BLUE = (153, 217, 234)
GREY = (140, 134, 133)

# Player sprite
PLAYER_IMAGE = pygame.image.load(os.path.join("Assets", "PlayerSprite.png"))
PLAYER_WIDTH, PLAYER_HEIGHT = 25, 35
PLAYER_IMAGE = pygame.transform.scale(PLAYER_IMAGE, (PLAYER_WIDTH, PLAYER_HEIGHT))
JUMP1 = pygame.image.load(os.path.join("Assets", "playerjump01.png"))
JUMP2 = pygame.image.load(os.path.join("Assets", "playerjump02.png"))
JUMP3 = pygame.image.load(os.path.join("Assets", "playerjump03.png"))
JUMP4 = pygame.image.load(os.path.join("Assets", "playerjump04.png"))
JUMP5 = pygame.image.load(os.path.join("Assets", "playerjump05.png"))
jumpanim = [JUMP1, JUMP2, JUMP3, JUMP4, JUMP5]

# Scaling each image
for i in range(0, 5):
    jumpanim[i] = pygame.transform.scale(jumpanim[i], (PLAYER_WIDTH, PLAYER_HEIGHT))

# Changing the window icon
pygame.display.set_icon(PLAYER_IMAGE)

# Platform sprite
PLATFORM_IMAGE = pygame.image.load(os.path.join("Assets", "PlatformSprite2.png"))
PLATFORM_WIDTH, PLATFORM_HEIGHT = 50, 7
PLATFORM_IMAGE = pygame.transform.scale(PLATFORM_IMAGE, (PLATFORM_WIDTH, PLATFORM_HEIGHT))

# Loading cloud images
CLOUD1 = pygame.image.load(os.path.join("Assets", "cloud1.png"))
CLOUD2 = pygame.image.load(os.path.join("Assets", "cloud2.png"))
CLOUD3 = pygame.image.load(os.path.join("Assets", "cloud3.png"))
CLOUD4 = pygame.image.load(os.path.join("Assets", "cloud4.png"))
CLOUD5 = pygame.image.load(os.path.join("Assets", "cloud5.png"))
CLOUDS = [CLOUD1, CLOUD2, CLOUD3, CLOUD4, CLOUD5]

# Loading power up sprites
JUMPBOOST = pygame.image.load(os.path.join("Assets", "jumpboost.png"))
JUMPBOOST = pygame.transform.scale(JUMPBOOST, (15, 20))

APPLE = pygame.image.load(os.path.join("Assets", "AppleSprite.png"))
APPLE = pygame.transform.scale(APPLE, (20, 20))

FORCEFIELD = pygame.image.load(os.path.join("Assets", "forcefield.png"))
FORCEFIELD = pygame.transform.scale(FORCEFIELD, (20, 20))

POWERUP_SPRITES = [APPLE, JUMPBOOST, FORCEFIELD]

# Additional images
LOGO = pygame.image.load(os.path.join("Assets", "gameLogo.png"))
LOGO = pygame.transform.scale(LOGO, (400, 100))

# Font for text
FONT = pygame.font.SysFont("comicsans", 20)
MENU_FONT = pygame.font.SysFont("comicsans", 30)

# Loading sounds
JUMPSOUND = pygame.mixer.Sound(os.path.join("Assets", "jumpsound.wav"))
JUMPBOOSTSOUND = pygame.mixer.Sound(os.path.join("Assets", "bigjumpsound.wav"))
GAMEOVERSOUND = pygame.mixer.Sound(os.path.join("Assets", "gameoversound.wav"))
SHIELDUPSOUND = pygame.mixer.Sound(os.path.join("Assets", "shieldupsound.wav"))
SHIELDBREAKSOUND = pygame.mixer.Sound(os.path.join("Assets", "shielddownsound.wav"))
APPLESOUND = pygame.mixer.Sound(os.path.join("Assets", "applesound.wav"))

SOUNDS = [JUMPSOUND, JUMPBOOSTSOUND, GAMEOVERSOUND, SHIELDBREAKSOUND, SHIELDUPSOUND, APPLESOUND]

# Player Class
class Player:

    # Constructor
    def __init__(self):
        self.image = jumpanim[0]
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        self.rect = self.image.get_rect()
        self.flip = False  # Used to flip the image if they change direction
        self.velocity = 0
        self.freeze = False
        self.apples = 0
        self.jumpboost = False
        self.protect = False
        self.forcefieldstart = False

        # Set the animation variables
        self.frame_index = 0
        self.frame_rate = 10
        self.frame_count = 0

    # Updating the animation
    def change_image(self):
        if self.frame_count % self.frame_rate == 0:
            self.frame_index = (self.frame_index + 1) % 5
        self.frame_count += 1

    # Enabling the forcefield
    def forcefield(self):
        self.protect = True
        self.forcefieldstart = True
        pygame.mixer.Sound.play(SHIELDUPSOUND)

    # Incrementing apples
    def addapple(self):
        self.apples += 1
        pygame.mixer.Sound.play(APPLESOUND)

    # Resets the players velocity
    def reset(self):
        self.velocity = 0
        self.protect = False
        self.forcefieldstart = False
        self.jumpboost = False
        self.apples = 0

    # Controls player movement
    def movement(self):
        
        # Increasing velocity due to gravity
        self.velocity += GRAVITY

        keys_pressed = pygame.key.get_pressed()  # Getting the key pressed
        if not self.freeze:
            if keys_pressed[pygame.K_a] or keys_pressed[pygame.K_LEFT]:  # Move left
                self.rect.x -= VELOCITY
                self.flip = True

            if keys_pressed[pygame.K_d] or keys_pressed[pygame.K_RIGHT]:  # Move right
                self.rect.x += VELOCITY
                self.flip = False

        # Checking if the player is falling
        if self.velocity < 0:
            isFalling = False
        else:
            isFalling = True

        # Jumping
        for platform in platforms:
            # Checking if the player has collided with the platform and if they are falling
            if platform.rect.colliderect(self.rect):
                if isFalling:
                    if player.rect.bottom >= platform.rect.top:
                        self.rect.bottom = platform.rect.top
                        self.velocity = 0  # Setting velocity to 0 so they can bounce up immediately
                        if self.jumpboost:
                            self.velocity += JUMPFORCE - 15
                            self.jumpboost = False
                            pygame.mixer.Sound.play(JUMPBOOSTSOUND)
                        else:
                            self.velocity += JUMPFORCE
                            pygame.mixer.Sound.play(JUMPSOUND)

        # Moving the platforms and powerups
        if self.rect.y < SCROLL_LINE:
            self.velocity += SCROLL_VELOCITY / 4
            scroll_amount = SCROLL_LINE -self.rect.y
            for platform in platforms:
                platform.rect.y += scroll_amount
                tracker.rect.y += scroll_amount

            for powerup in powerups:
                powerup.rect.y += scroll_amount
            self.rect.y = SCROLL_LINE

        # Adjusting the players y velocity
        if self.freeze == False:
            self.rect.y += self.velocity

    def jump(self):
        self.velocity = 0  # Setting velocity to 0 so they can bounce up immediately
        self.velocity += JUMPFORCE  # Speed / height the player jumps at

    # Checks if the player is within the boundaries of the game
    def boundaries(self):
        
        # Left side
        if self.rect.right < 0:
            self.rect.left = WIDTH # Moves the player to the right side of the screen

        # Right side
        if self.rect.left > WIDTH:
            self.rect.right = 0  # Moves the player to the left side of the screen

    # Drawing the sprite onto the screen
    def draw(self):
        self.change_image()
        player.boundaries()
        player.movement()
        SCREEN.blit(pygame.transform.flip(jumpanim[self.frame_index], self.flip, False), (self.rect.x - 2, self.rect.y - 1))

# Platform class
class Platform(pygame.sprite.Sprite):
    # Constructor
    def __init__(self, x, y, moving):
        pygame.sprite.Sprite.__init__(self)
        self.image = PLATFORM_IMAGE
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        
# Cloud class
class Cloud(pygame.sprite.Sprite):
    # Constructor
    def __init__(self, x, y, cloud_image, start_side, vel):
        pygame.sprite.Sprite.__init__(self)
        self.image = cloud_image
        self.rect = self.image.get_rect()
        self.x = x
        self.y = y
        self.rect.x = self.x
        self.rect.y = self.y
        self.start = start_side
        self.velocity = vel


# Power up class
class Powerup(pygame.sprite.Sprite):
    def __init__(self, x, y, powerup_sprite, type):
        pygame.sprite.Sprite.__init__(self)
        self.image = powerup_sprite
        self.rect = self.image.get_rect()
        self.rect.x = x
        self.rect.y = y
        self.type = type

    # Adding an apples
    def apple(self):
        player.addapple()

    # Enabling jump boost
    def jumpboost(self):
        player.jumpboost = True

    # Enabling the forcefield
    def forcefield(self):
        player.forcefield()

    # Checking which action should be used
    def action(self):
        if self.type == "apple":
            self.apple()

        if self.type == "jumpboost":
            self.jumpboost()

        if self.type == "forcefield":
            self.forcefield()

# Powerup sprite group
powerups = pygame.sprite.Group()

# Choosing a random powerup
def select_powerup():
    num = random.randint(0, len(POWERUP_SPRITES) - 1)
    if num == 0:
        return POWERUP_SPRITES[0], "apple"
    if num == 1:
        return POWERUP_SPRITES[1], "jumpboost"
    if num == 2:
        return POWERUP_SPRITES[2], "forcefield"

# Adding a powerup to the sprite group
def create_powerup(x, y):
    sprite, type = select_powerup()
    powerup = Powerup(x, y, sprite, type)
    powerups.add(powerup)

# Removing the powerups
def manage_powerup():
    for powerup in powerups:
        # Removing if it collides with the player
        if powerup.rect.colliderect(player.rect):
            powerup.action()
            powerups.remove(powerup)

        # Removing if it goes off screen
        if powerup.rect.y > HEIGHT:
            powerups.remove(powerup)


# Button class
class Button():
    # Constructor
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.width = 150
        self.height = 75
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)

    # Drawing the button
    def draw(self):
        pygame.draw.rect(SCREEN, self.hover(), self.rect, 0)

    # Shading the button grey when the mouse hovers over it
    def hover(self):
        mousex, mousey = pygame.mouse.get_pos()

        if self.x < mousex < self.x + self.width and self.y < mousey < self.y + self.height:
            colour = GREY
        else:
            colour = BG_BLUE

        return colour

    # Checking if the button is clicked
    def clicked(self):
        mouse_input = pygame.mouse.get_pressed()
        mousex, mousey = pygame.mouse.get_pos()
        if self.x < mousex < self.x + self.width and self.y < mousey < self.y + self.height:
            if mouse_input[0]:
                pygame.time.delay(100)
                return True
            
    # Drawing text
    def text(self, string, x, y):
        text = MENU_FONT.render(string, True, BLACK)
        SCREEN.blit(text, (x, y))


# Creating the player object
player = Player()

# Creating platform sprite group
platforms = pygame.sprite.Group()

# Creating a tracker for distance
tracker = Platform(200, 490, False)

# Creating cloud sprite group
clouds = pygame.sprite.Group()

# Maximum characters when entering name
max_name_length = 10


# Randomly selecting a cloud sprite to use
def getCloudImage():
    num = random.randint(0, len(CLOUDS) - 1)
    current_cloud = CLOUDS[num]
    return current_cloud


# Spawning clouds
def spawn_clouds():
    if len(clouds) > 0:
        for cloud in clouds:
            # Removing clouds depending on the side they start on
            if cloud.start == "left":
                if cloud.rect.x > WIDTH:
                    clouds.remove(cloud)
            if cloud.start == "right":
                if cloud.rect.x < 0 - cloud.rect.width:
                    clouds.remove(cloud)
            if cloud.rect.top > HEIGHT:
                clouds.remove(cloud)

    # Spawning clouds while there aren't enough on screen
    while len(clouds) < MAX_CLOUDS:
        x_pos = 0
        start_side = "null"
        rand_cloud = getCloudImage()
        cloud = Cloud(0, 0, getCloudImage(), 0, 0)

        randx = random.randint(1, 2)
        if randx == 1:  # Left side
            start_side = "left"
            x_pos = abs(random.randint(cloud.rect.width, (cloud.rect.width * 2)))
            x_pos = 0 - x_pos

        if randx == 2:  # Right side
            start_side = "right"
            x_pos = random.randint(WIDTH + cloud.rect.width, WIDTH + (cloud.rect.width * 2))

        # Creating then adding the cloud object to the pygame group
        y_pos = random.randint(0 + cloud.rect.height, HEIGHT - cloud.rect.height)
        cloud = Cloud(x_pos, y_pos, rand_cloud, start_side, CLOUD_VELOCITY)
        clouds.add(cloud)


# Controlling the movement of the clouds
def move_clouds():
    for cloud in clouds:
        if cloud.start == "left":
            cloud.rect.x += cloud.velocity
        if cloud.start == "right":
            cloud.rect.x -= cloud.velocity


# Spawning initial platforms
def start_platforms():

    # Setting the players starting position
    player.rect.x = 200
    player.rect.y = 450

    # Creating a platform for the player to start on
    platform = Platform(200, 490, False)
    platforms.add(platform)

    y_val = HEIGHT - HEIGHT / MAX_PLATFORMS

    # Spawns in the starting platforms
    for i in range(0, MAX_PLATFORMS - 1):
        randx = random.randint(0, WIDTH - PLATFORM_WIDTH + 10)  # Chooses a random x value
        platform = Platform(randx, y_val, False)
        y_val -= HEIGHT / MAX_PLATFORMS  # Increases the layer the next platform will spawn on
        platforms.add(platform)

# Spawns platforms
def create_platforms(start):
    powerup_num = random.randint(1, 10)
    randx = random.randint(0 - 20, WIDTH - PLATFORM_WIDTH + 10)
    if start:
        start_platforms()

    # Creates platforms when a platform goes off screen
    else:
        for platform in platforms:   
            if platform.rect.y > HEIGHT:  # Checks and removes if a platform comes off the screen
                platforms.remove(platform)

        # Adds a platform if there is less than the maximum and there is a certain distance between the previous platform
        if platforms.__len__() < MAX_PLATFORMS:
            last_platform = platforms.sprites()[-1]
            if last_platform.rect.y > 100:
                platform = Platform(randx, 0, True)
                platforms.add(platform)

                # Spawning power ups with a 1/10 chance
                if powerup_num == 1:
                    create_powerup(randx + 15, -20)
                    
    # Updating the powerup        
    manage_powerup()


# Game end screen
def end_game(time_played, apples, distance, buttonpress, user_input, user_typing):
    SCREEN.fill(WHITE)
    # Displaying text box when the user presses the add to leaderboard button
    if user_typing:
        typing_info = MENU_FONT.render("Enter your name here:", True, BLACK)
        SCREEN.blit(typing_info, (50, 85))
        
        user_input_rect = pygame.Rect(50,110,300, 32)
        pygame.draw.rect(SCREEN, BLACK, user_input_rect, 2)
        text_surface = MENU_FONT.render(user_input, True, BLACK)
        SCREEN.blit(text_surface, (user_input_rect.x + 5, user_input_rect.y + 5))

    # Displaying buttons
    add_score_button(buttonpress)
    restart_button()
    home_button()

    # Displaying score text
    score_text = MENU_FONT.render(("Your score was: " + str(round(time_played + apples + distance))), True, BLACK)
    SCREEN.blit(score_text, (115, 30))

    # Updating pygame window
    pygame.display.update()


# Main menu button
def home_button():
    home_button = Button(125, 350)
    home_button.draw()
    home_button.text("Main Menu", home_button.x + 25, home_button.y + 20)
    home_button.text("(M)", home_button.x + 62, home_button.y + 40)
    if home_button.clicked():
        return True


# Restart button
def restart_button():
    restart_button = Button(125, 250)
    restart_button.draw()
    restart_button.text("Restart", restart_button.x + 43, restart_button.y + 20)
    restart_button.text("(R)", restart_button.x + 62, restart_button.y + 40)
    if restart_button.clicked():
        return True


# Add to leaderboard button
def add_score_button(buttonpress):
    add_score_button = Button(125, 150)
    add_score_button.draw()

    # Changing the text when the button has been pressed
    if buttonpress:
        add_score_button.text("Added to", add_score_button.x + 35, add_score_button.y + 20)
        add_score_button.text("leaderboard!!", add_score_button.x + 12, add_score_button.y + 40)

    else:
        add_score_button.text("Add to", add_score_button.x + 45, add_score_button.y + 10)
        add_score_button.text("leaderboard", add_score_button.x + 18, add_score_button.y + 30)
        add_score_button.text("(L)", add_score_button.x + 62, add_score_button.y + 50)

    if add_score_button.clicked():
        return True


# Drawing onto the screen
def draw_window(time_played, distance, apples, forcefieldtime, pause, sounds, dead):
    if pause == False and dead == False:
        # Drawing the background
        SCREEN.fill(BG_BLUE)

        # Draws clouds
        clouds.draw(SCREEN)

        # Draws platforms
        platforms.draw(SCREEN)

        # Draws power ups
        powerups.draw(SCREEN)

        # Draws player
        player.draw()

        # Drawing the current time onto the screen. Rounds the time so it is readable
        timer_text = FONT.render("Time: " + str(round(time_played)), True, (255, 255, 255))
        SCREEN.blit(timer_text, (0, 5))

        # Drawing distance onto the screen. Rounds the distance so it is readable
        distance_text = FONT.render("Distance: " + str(round(distance)), True, [255, 255, 255])
        SCREEN.blit(distance_text, (0, 20))

        # Drawing total apples onto the screen
        apples_text = FONT.render("Apples: " + str(apples), True, (255, 255, 255))
        SCREEN.blit(apples_text, (0, 35))

        # Displaying time left for the forcefield
        if player.protect:
            protection_text = FONT.render("Protection for " + str(round(forcefieldtime)) + "s", True, WHITE)
            SCREEN.blit(protection_text, (0, 100))

    # Displaying the pause menu
    if pause:
        SCREEN.fill(WHITE)

        # Pause menu text
        temp_text = MENU_FONT.render("Pause menu, B to go back", True, BLACK)
        SCREEN.blit(temp_text, (0, HEIGHT - 30))
        text0 = MENU_FONT.render("Controls:", True, BLACK)
        text1 = MENU_FONT.render("Use 'A'(left) or 'D'(right)", True, BLACK)
        text2 = MENU_FONT.render("or the Arrow keys to move", True, BLACK)
        text3 = MENU_FONT.render("Move further up to gain score", True, BLACK)
        text4 = MENU_FONT.render("Apples give 10 score", True, BLACK)

        # Drawing the text
        SCREEN.blit(text0, (0, 0))
        SCREEN.blit(text1, (0, 20))
        SCREEN.blit(text2, (0, 40))
        SCREEN.blit(text3, (0, 100))
        SCREEN.blit(text4, (0, 120))


       # Toggle sound button
        sound_button(sounds)

    pygame.display.update()


# Add username and scores to leaderboard
def leaderboard_append(username, score, leaderboard_list):
    leaderboard_list.append((username, score))
    file = open("leaderboard.txt", "wb")
    leaderboard_list = sorted(leaderboard_list, key=itemgetter(1), reverse=True)
    pickle.dump(leaderboard_list, file)
    file.close

    save_leaderboard(leaderboard_list)


# Save the current state of the leaderboard
def save_leaderboard(leaderboard_list):
    file = open("leaderboard.txt", "wb")
    pickle.dump(sorted(leaderboard_list, key=itemgetter(1), reverse=True), file)
    file.close


# Load the saved leaderboard
def load_leaderboard():
    file = open("leaderboard.txt", "rb")
    leaderboard_list = sorted(pickle.load(file), key=itemgetter(1), reverse=True)
    file.close
    return leaderboard_list

# Setting the volume of the sounds to 100
def enable_sound():
    for i in range(0, len(SOUNDS) - 1):
        pygame.mixer.Sound.set_volume(SOUNDS[i], 100)

# Setting the volume of the sounds to 0
def disable_sound():
    for i in range(0, len(SOUNDS) - 1):
        pygame.mixer.Sound.set_volume(SOUNDS[i], 0)


# Main game loop
def main_game():
    # Main game variables
    run = True
    start = True
    dead = False
    pause = False
    l_input = False
    forcefieldstart = 0
    timeleft = 0
    sounds = True
    buttonflag = False
    soundflag = True
    text_input = False
    user_input = ""
    
    # Main menu variables
    menu = True
    leaderboard_menu = False
    options_menu = False
    gameover = False
    leaderboard = load_leaderboard()

    while run:
        clock.tick(FPS)
        keys_pressed = pygame.key.get_pressed()  # Getting the key pressed

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                run = False

            elif text_input:
                if event.type == pygame.KEYDOWN:
                    if event.unicode.isalnum() and len(user_input) < max_name_length:
                        user_input += event.unicode
                    if event.key == pygame.K_BACKSPACE:
                        user_input = user_input[:-1]
                    if event.key == pygame.K_RETURN: #keys_pressed[pygame.K_RETURN]:
                        user_name = user_input
                        score = round(distance + player.apples * 10 + time_played)
                        leaderboard_append(user_name, int(score), leaderboard)
                        l_input = True
                        text_input = False

        # Displaying main menu
        if menu:

            # Options menu
            if options_menu == True:

                # Toggle sounds button
                if sound_button(sounds):

                    if sounds == True and buttonflag == False:
                        disable_sound()
                        sounds = False
                        buttonflag = True

                    if sounds == False and buttonflag == False:
                        enable_sound()
                        sounds = True

                    buttonflag = False

                # Reset leaderboard button
                if reset_leaderboard_button():
                    leaderboard = [("---", 0), ("---", 0), ("---", 0), ("---", 0), ("---", 0),
                                   ("---", 0), ("---", 0), ("---", 0), ("---", 0), ("---", 0)]
                    save_leaderboard(leaderboard)

            # Main menu screen
            if leaderboard_menu == False and options_menu == False:

                # Button functions
                if play_button() or keys_pressed[pygame.K_p]:  # Play game
                    menu = False
                    gameover = False

                    # Starts the timer for the user when they begin to play
                    start_time = time.time()

                if leaderboard_button() or keys_pressed[pygame.K_l]:  # Open leaderboard screen
                    leaderboard_menu = True

                if quit_button() or keys_pressed[pygame.K_q]:  # Quit
                    run = False

                if options_button() or keys_pressed[pygame.K_o] or options_menu:  # Options screen
                    options_menu = True

            if options_menu or leaderboard_menu:
                if back_button() or keys_pressed[pygame.K_ESCAPE]:  # Back button
                    options_menu = False
                    leaderboard_menu = False

            # Drawing the main menu
            draw_main_menu(options_menu, leaderboard_menu, sounds, leaderboard)

        elif menu == False:

            if dead == False and pause == False:
                # Platform spawning
                create_platforms(start)
                start = False

                # Cloud spawning
                spawn_clouds()
                move_clouds()

                # Getting the time played from when the player pressed start
                time_played = time.time() - start_time

                # Gets the distance from the amount of pixels the tracker has moved
                distance = tracker.rect.y // 100 -4
            if gameover == False:
                draw_window(time_played, distance, player.apples, timeleft, pause, sounds, dead)

            # Getting the time elapsed for the forcefield
            if player.forcefieldstart:
                forcefieldstart = time.time()
                player.forcefieldstart = False

            # Breaking the forcefield
            if player.protect:
                timeleft = 10 - abs(forcefieldstart - time.time())
                if round(timeleft) == 0:
                    player.protect = False
                    pygame.mixer.Sound.play(SHIELDBREAKSOUND)

            if keys_pressed[pygame.K_ESCAPE]:  # Pause screen
                pause = True
                player.freeze = True

            if pause:
                if keys_pressed[pygame.K_b]:  # to go back to the game
                    pause = False
                    player.freeze = False

                if sound_button(sounds):

                    if sounds == True and buttonflag == False:
                        disable_sound()
                        sounds = False
                        buttonflag = True

                    if sounds == False and buttonflag == False:
                        enable_sound()
                        sounds = True

                    buttonflag = False

            # Checking if the player has hit the bottom
            if player.rect.bottom >= HEIGHT:

                # Breaking the forcefield
                if player.protect:
                    player.rect.bottom = HEIGHT
                    pygame.mixer.Sound.play(SHIELDBREAKSOUND)
                    player.jump()
                    player.protect = False

                # Ending the game
                elif not gameover:
                    if soundflag:
                        pygame.mixer.Sound.play(GAMEOVERSOUND)
                        soundflag = False
                        gameover = True
            # Displaying the end game screen
            if gameover:
                end_game(time_played, distance, player.apples * 10, l_input, user_input, text_input)
                dead = True
                
                if not text_input:
                    # Resetting the game if the user dies
                    if keys_pressed[pygame.K_r] or restart_button():

                        tracker.rect.y = 490
                        start_time = time.time()
                        player.reset()
                        
                        for platform in platforms:
                            platforms.remove(platform)

                        for powerup in powerups:
                            powerups.remove(powerup)

                        l_input = False
                        dead = False
                        start = True
                        gameover = False
                        soundflag = True

                    # Back to main menu button pressed
                    if keys_pressed[pygame.K_m] or home_button():
                        player.reset()
                        tracker.rect.y = 490

                        for platform in platforms:  # Removing the platforms from the previous attempt
                            platforms.remove(platform)
                        for powerup in powerups:
                            powerups.remove(powerup)

                        dead = False
                        l_input = False
                        start = True
                        menu = True
                        soundflag = True
                        gameover = False

                    if (keys_pressed[pygame.K_l] or add_score_button(l_input)) and l_input == False:  # Add score to leaderboard
                        text_input = True
                    
    save_leaderboard(leaderboard)
    pygame.quit()

# Text input box
def text_input_box(user_input):
    user_input_rect = pygame.Rect(100,0,300, 32)
    pygame.draw.rect(SCREEN, WHITE, user_input_rect, 2)
    text_surface = FONT.render(user_input, True, WHITE)
    SCREEN.blit(text_surface, (user_input_rect.x + 5, user_input_rect.y + 5))
    pygame.display.update()
    print(user_input)

# Main menu screen
def draw_main_menu(options_menu, leaderboard_menu, sounds, leaderboard):
    leaderboard = sorted(leaderboard, key=itemgetter(1), reverse=True)
    SCREEN.fill(WHITE)
    if options_menu == False and leaderboard_menu == False:
        play_button()
        options_button()
        quit_button()
        leaderboard_button()
        SCREEN.blit(LOGO, (0, 0))

    if leaderboard_menu == True:
        back_button()
        # Drawing the top 10 scores onto the leaderboard
        yval = 100
        for i in range(0, 10):
            item = leaderboard[i]
            username = item[0]
            score = item[1]
            text = MENU_FONT.render((str(i + 1) + ") " + username + ": " + str(score)), True, BLACK)
            SCREEN.blit(text, (5, yval))
            yval = yval + 40

    # Displaying the options menu
    if options_menu == True:
        SCREEN.fill(WHITE)
        back_button()
        reset_leaderboard_button()
        sound_button(sounds)

    pygame.display.update()


# Open leaderboard button
def leaderboard_button():
    leaderboard_button = Button(125, 190)
    leaderboard_button.draw()
    leaderboard_button.text("View", leaderboard_button.x + 55, leaderboard_button.y + 10)
    leaderboard_button.text("leaderboard", leaderboard_button.x + 18, leaderboard_button.y + 30)
    leaderboard_button.text("(L)", leaderboard_button.x + 62, leaderboard_button.y + 50)
    
    if leaderboard_button.clicked():
        return True


# Play button
def play_button():
    play_button = Button(125, 100)
    play_button.draw()
    play_button.text("Play", play_button.x + 55, play_button.y + 25)
    play_button.text("(P)", play_button.x + 62, play_button.y + 45)
    if play_button.clicked():
        return True


# Options button
def options_button():
    options_button = Button(125, 285)
    options_button.draw()
    options_button.text("Options", options_button.x + 40, options_button.y + 20)
    options_button.text("(O)", options_button.x + 62, options_button.y + 40)
    if options_button.clicked():
        return True


# Quit game button
def quit_button():
    quit_button = Button(125, 375)
    quit_button.draw()
    quit_button.text("Quit", quit_button.x + 55, quit_button.y + 20)
    quit_button.text("(Q)", quit_button.x + 62, quit_button.y + 40)
    if quit_button.clicked():
        return True


# Button to go back to the main menu from options and leaderboard
def back_button():
    back_button = Button(0, 0)
    back_button.draw()
    back_button.text("Back", back_button.x + 50, back_button.y + 20)
    back_button.text("(ESC)", back_button.x + 48, back_button.y + 40)
    if back_button.clicked():
        return True

# Sounds button
def sound_button(sounds):
    sound_button = Button(125, 150)
    sound_button.draw()
    sound_button.text("Toggle Sound:", sound_button.x + 8, sound_button.y + 20)

    # Changing the text if sound is on/off
    if sounds:
        sound_button.text("on", sound_button.x + 60, sound_button.y + 40)

    elif sounds == False:
        sound_button.text("off", sound_button.x + 60, sound_button.y + 40)

    if sound_button.clicked():
        return True

# Reset leaderboard button
def reset_leaderboard_button():
    reset_button = Button(125, 250)
    reset_button.draw()
    reset_button.text("Reset", reset_button.x + 48, reset_button.y + 20)
    reset_button.text("Leaderboard", reset_button.x + 15, reset_button.y + 40)
    if reset_button.clicked():
        return True


if __name__ == "__main__":
    main_game()
