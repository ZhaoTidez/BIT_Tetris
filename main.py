import pygame
import random
import sys
import time
import os
from dataclasses import dataclass
from typing import List, Tuple, Optional

# 初始化Pygame
pygame.init()


# 常量定义
@dataclass
class Constants:
    SCREEN_WIDTH = 400  # 原宽度300 + 100侧边栏
    SCREEN_HEIGHT = 600
    GAME_AREA_WIDTH = 300
    SIDEBAR_WIDTH = SCREEN_WIDTH - GAME_AREA_WIDTH

    # 颜色定义
    WHITE = (255, 255, 255)
    BLACK = (0, 0, 0)
    GRAY = (169, 169, 169)
    RED = (255, 0, 0)
    CYAN = (0, 255, 255)
    MAGENTA = (255, 0, 255)
    BLUE = (0, 0, 255)
    GREEN = (0, 255, 0)
    YELLOW = (255, 255, 0)
    DARK_GRAY = (50, 50, 50)
    LIGHT_GRAY = (100, 100, 100)

    # 游戏设置
    BLOCK_SIZE = 30
    GRID_WIDTH = 10
    GRID_HEIGHT = 20
    SKILL_COOLDOWN = 45
    SETTINGS_FILE = "settings/tetris_settings.txt"
    HIGH_SCORE_FILE = "settings/high_score.txt"

    INITIAL_MOVE_DELAY = 1000  # 初始延迟（毫秒）
    REPEAT_MOVE_DELAY = 100  # 重复延迟（毫秒）
    MIN_REPEAT_DELAY = 50  # 最小重复延迟
    MAX_REPEAT_DELAY = 300  # 最大重复延迟

    SHAPES = [
        [[1, 1, 1, 1]],  # I形
        [[1, 1, 1], [0, 0, 1]],  # L形
        [[1, 1, 1], [1, 0, 0]],  # J形
        [[1, 1], [1, 1]],  # O形
        [[1, 1, 0], [0, 1, 1]],  # S形
        [[0, 1, 1], [1, 1, 0]],  # Z形
        [[1, 1, 1], [0, 1, 0]]  # T形
    ]

    SHAPE_COLORS = [
        CYAN, RED, MAGENTA,
        WHITE, GREEN, YELLOW, BLUE
    ]


class GameSettings:
    """游戏设置类，管理音效和音乐设置"""

    def __init__(self):
        self.music_enabled = True
        self.sound_enabled = True
        self.show_help = not self.load_settings()
        self.repeat_delay = Constants.REPEAT_MOVE_DELAY  # 默认重复延迟
        self._init_sounds()

    def _init_sounds(self):
        """初始化音效"""
        try:
            pygame.mixer.init()
            self.line_clear_sound = pygame.mixer.Sound("music/line_clear.wav")
            self.rotate_sound = pygame.mixer.Sound("music/rotate.wav")
            self.game_over_sound = pygame.mixer.Sound("music/end.wav")
            self.special_skill_sound = pygame.mixer.Sound("music/skill.wav")
            pygame.mixer.music.load("music/background.mp3")
            pygame.mixer.music.set_volume(0.6)
            if self.music_enabled:
                pygame.mixer.music.play(-1, 0.0)
        except Exception as e:
            print(f"警告：音效文件加载失败: {e}")
            self.sound_enabled = False
            self.music_enabled = False

    def load_settings(self) -> bool:
        """加载设置，决定是否显示帮助"""
        try:
            with open(Constants.SETTINGS_FILE, "r") as f:
                lines = f.readlines()
                if len(lines) > 0:
                    first_line = lines[0].strip()
                    if first_line == "hide_help":
                        # 如果有第二行，读取灵敏度设置
                        if len(lines) > 1:
                            try:
                                self.repeat_delay = int(lines[1].strip())
                                # 确保值在合理范围内
                                self.repeat_delay = max(Constants.MIN_REPEAT_DELAY,
                                                        min(Constants.MAX_REPEAT_DELAY, self.repeat_delay))
                            except ValueError:
                                pass
                        return True
                return False
        except (FileNotFoundError, IOError):
            return False

    def save_settings(self, hide_help: bool) -> None:
        """保存设置"""
        try:
            with open(Constants.SETTINGS_FILE, "w") as f:
                f.write("hide_help\n" if hide_help else "show_help\n")
                f.write(str(self.repeat_delay))  # 保存当前灵敏度设置
        except IOError as e:
            print(f"无法保存设置: {e}")

    def play_sound(self, sound) -> None:
        """播放音效"""
        if self.sound_enabled:
            try:
                sound.play()
            except Exception as e:
                print(f"播放音效失败: {e}")

    def toggle_music(self) -> None:
        """切换音乐开关"""
        self.music_enabled = not self.music_enabled
        if self.music_enabled:
            try:
                pygame.mixer.music.play(-1, 0.0)
            except Exception as e:
                print(f"播放音乐失败: {e}")
                self.music_enabled = False
        else:
            pygame.mixer.music.pause()

    def toggle_sound(self) -> None:
        """切换音效开关"""
        self.sound_enabled = not self.sound_enabled

    def set_repeat_delay(self, delay: int) -> None:
        """设置重复延迟时间"""
        self.repeat_delay = max(Constants.MIN_REPEAT_DELAY, min(Constants.MAX_REPEAT_DELAY, delay))


class Tetrimino:
    """方块类，表示游戏中的一个方块"""

    def __init__(self, shape: List[List[int]], color: Tuple[int, int, int]):
        self.shape = shape
        self.color = color
        self.x = Constants.GRID_WIDTH // 2 - len(shape[0]) // 2
        self.y = 0
        self.rotation = 0

    def rotate(self, grid: List[List[int]], settings: GameSettings) -> None:
        """旋转方块"""
        original_shape = self.shape[:]
        self.shape = [list(row) for row in zip(*self.shape[::-1])]  # 逆时针旋转90度

        if not self.valid_move(grid, 0, 0):
            self.shape = original_shape
        else:
            settings.play_sound(settings.rotate_sound)

    def draw(self, surface: pygame.Surface, pattern_img: Optional[pygame.Surface] = None) -> None:
        """绘制方块"""
        for row in range(len(self.shape)):
            for col in range(len(self.shape[row])):
                if self.shape[row][col]:
                    # 绘制底色
                    pygame.draw.rect(surface, self.color,
                                     ((self.x + col) * Constants.BLOCK_SIZE,
                                      (self.y + row) * Constants.BLOCK_SIZE,
                                      Constants.BLOCK_SIZE, Constants.BLOCK_SIZE))

                    # 叠加图案（如果图片加载成功）
                    if pattern_img:
                        surface.blit(pattern_img,
                                     ((self.x + col) * Constants.BLOCK_SIZE,
                                      (self.y + row) * Constants.BLOCK_SIZE))

                    # 绘制边框
                    pygame.draw.rect(surface, Constants.BLACK,
                                     ((self.x + col) * Constants.BLOCK_SIZE,
                                      (self.y + row) * Constants.BLOCK_SIZE,
                                      Constants.BLOCK_SIZE, Constants.BLOCK_SIZE), 1)

    def valid_move(self, grid: List[List[int]], dx: int, dy: int) -> bool:
        """检查移动是否有效"""
        for row in range(len(self.shape)):
            for col in range(len(self.shape[row])):
                if self.shape[row][col]:
                    x_pos = self.x + col + dx
                    y_pos = self.y + row + dy
                    if x_pos < 0 or x_pos >= Constants.GRID_WIDTH or y_pos >= Constants.GRID_HEIGHT:
                        return False
                    if y_pos >= 0 and grid[y_pos][x_pos]:
                        return False
        return True

    def move(self, grid: List[List[int]], dx: int, dy: int) -> bool:
        """移动方块"""
        if self.valid_move(grid, dx, dy):
            self.x += dx
            self.y += dy
            return True
        return False


class GameState:
    """游戏状态类，管理游戏的核心逻辑"""

    def __init__(self, settings: GameSettings):
        self.settings = settings
        self.reset()
        self.held_keys = {
            pygame.K_LEFT: False,
            pygame.K_RIGHT: False,
            pygame.K_DOWN: False
        }
        self.last_move_time = {
            pygame.K_LEFT: 0,
            pygame.K_RIGHT: 0,
            pygame.K_DOWN: 0
        }
        self.move_delay = Constants.INITIAL_MOVE_DELAY  # 使用常量

    def reset(self) -> None:
        """重置游戏状态"""
        self.grid = [[0 for _ in range(Constants.GRID_WIDTH)] for _ in range(Constants.GRID_HEIGHT)]
        self.score = 0
        self.last_skill_time = -Constants.SKILL_COOLDOWN  # 初始时技能可用
        self.current_tetrimino = self.new_tetrimino()
        self.next_tetrimino = self.new_tetrimino()
        self.falling_speed = 500
        self.last_fall_time = pygame.time.get_ticks()
        self.total_lines_cleared = 0
        self.game_over = False
        self.paused = False

    def new_tetrimino(self) -> Tetrimino:
        """生成新方块"""
        shape_idx = random.randint(0, len(Constants.SHAPES) - 1)
        return Tetrimino(Constants.SHAPES[shape_idx], Constants.SHAPE_COLORS[shape_idx])

    def clear_lines(self) -> int:
        """消除行并增加得分"""
        new_grid = [row for row in self.grid if any(cell == 0 for cell in row)]
        lines_cleared = Constants.GRID_HEIGHT - len(new_grid)

        if lines_cleared > 0:
            self.settings.play_sound(self.settings.line_clear_sound)
            self.score += 50 * (2 ** lines_cleared - 1)

        self.grid = [[0 for _ in range(Constants.GRID_WIDTH)] for _ in range(lines_cleared)] + new_grid
        return lines_cleared

    def clear_last_three_rows(self) -> bool:
        """消除最后三排的技能"""
        current_time = time.time()

        # 检查技能是否在冷却中
        if current_time - self.last_skill_time < Constants.SKILL_COOLDOWN:
            return False

        if Constants.GRID_HEIGHT < 3:  # 确保有足够行数
            return False

        # 检查最后三排是否有方块
        has_blocks = any(
            self.grid[y][x] != 0
            for y in range(Constants.GRID_HEIGHT - 3, Constants.GRID_HEIGHT)
            for x in range(Constants.GRID_WIDTH)
        )

        if not has_blocks:
            return False  # 最后三排没有方块，不执行

        # 消除最后三排
        for y in range(Constants.GRID_HEIGHT - 3, Constants.GRID_HEIGHT):
            for x in range(Constants.GRID_WIDTH):
                self.grid[y][x] = 0

        # 将上面的方块向下平移三格
        new_grid = [[0 for _ in range(Constants.GRID_WIDTH)] for _ in range(3)]  # 新增三行空白
        new_grid.extend(row[:] for row in self.grid[:-3])  # 将原有行下移

        self.grid = new_grid
        self.score += 100  # 固定得分奖励
        self.last_skill_time = current_time  # 更新最后使用技能时间

        self.settings.play_sound(self.settings.special_skill_sound)
        return True

    def update(self) -> None:
        """更新游戏状态"""
        if self.paused or self.game_over:
            return

        current_time = pygame.time.get_ticks()

        # 处理持续按键移动
        for key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN]:
            if self.held_keys[key]:
                time_since_last = current_time - self.last_move_time[key]

                # 判断是否应该移动
                should_move = False

                # 如果是第一次按键后还没移动过
                if self.last_move_time[key] == 0:
                    should_move = time_since_last > self.move_delay
                else:
                    should_move = time_since_last > self.settings.repeat_delay  # 使用设置中的延迟

                if should_move:
                    if key == pygame.K_LEFT:
                        self.current_tetrimino.move(self.grid, -1, 0)
                    elif key == pygame.K_RIGHT:
                        self.current_tetrimino.move(self.grid, 1, 0)
                    elif key == pygame.K_DOWN:
                        self.current_tetrimino.move(self.grid, 0, 1)
                    self.last_move_time[key] = current_time

        # 方块自动下落
        if current_time - self.last_fall_time > self.falling_speed:
            if not self.current_tetrimino.move(self.grid, 0, 1):  # 传递self.grid参数
                # 固定当前方块
                for row in range(len(self.current_tetrimino.shape)):
                    for col in range(len(self.current_tetrimino.shape[row])):
                        if self.current_tetrimino.shape[row][col]:
                            self.grid[self.current_tetrimino.y + row][
                                self.current_tetrimino.x + col] = self.current_tetrimino.color
                self.last_fall_time = current_time

                lines_cleared = self.clear_lines()
                self.total_lines_cleared += lines_cleared

                # 随着消除行数增加，提高下落速度
                if self.total_lines_cleared >= 10:
                    self.falling_speed = max(100, self.falling_speed - 50)
                    self.total_lines_cleared -= 10

                self.current_tetrimino = self.next_tetrimino
                self.next_tetrimino = self.new_tetrimino()

                # 检查游戏是否结束
                if not self.current_tetrimino.valid_move(self.grid, 0, 0):
                    self.game_over = True
                    pygame.mixer.music.pause()
                    self.settings.play_sound(self.settings.game_over_sound)

            self.last_fall_time = current_time


class GameRenderer:
    """游戏渲染类，负责所有绘制工作"""

    def __init__(self, screen: pygame.Surface, settings: GameSettings):
        self.screen = screen
        self.settings = settings
        self.pattern_img = self._load_pattern_image()
        self.slider_dragging = False  # 标记滑块是否被拖动

    def _load_pattern_image(self) -> Optional[pygame.Surface]:
        """加载方块图案图片"""
        try:
            pattern_img = pygame.image.load("block.png").convert_alpha()
            return pygame.transform.scale(pattern_img, (Constants.BLOCK_SIZE, Constants.BLOCK_SIZE))
        except Exception as e:
            print(f"警告：图案图片加载失败: {e}")
            return None

    def draw_start_screen(self, hide_help: bool) -> None:
        """绘制开始界面"""
        self.screen.fill(Constants.BLACK)

        # 绘制标题
        title_font = pygame.font.SysFont("Microsoft YaHei", 36)
        title_text = title_font.render("北理工方块", True, Constants.WHITE)
        self.screen.blit(title_text, (Constants.SCREEN_WIDTH // 2 - title_text.get_width() // 2, 50))

        # 绘制操作说明
        font = pygame.font.SysFont("Microsoft YaHei", 20)
        controls = [
            "注意：",
            "请关闭输入法进行游玩",
            "操作说明:",
            "← → : 左右移动",
            "↑ : 旋转方块",
            "↓ : 加速下落（可按住）",
            "回车 : 暂停/继续",
            "ESC : 退出游戏",
            "R : 重新开始",
            "S : 重置最高分",
            "F : 坦克碾压（消除最后三排）",
            f"技能冷却时间: {Constants.SKILL_COOLDOWN}秒"
        ]

        for i, line in enumerate(controls):
            text = font.render(line, True, Constants.WHITE)
            self.screen.blit(text, (50, 100 + i * 30))

        # 绘制开始按钮
        start_font = pygame.font.SysFont("Microsoft YaHei", 28)
        start_text = start_font.render("按空格键开始游戏", True, Constants.WHITE)
        self.screen.blit(start_text, (Constants.SCREEN_WIDTH // 2 - start_text.get_width() // 2, 500))

        # 绘制不再显示选项
        checkbox_font = pygame.font.SysFont("Microsoft YaHei", 20)
        checkbox_text = checkbox_font.render("不再显示此提示（按H可恢复）", True, Constants.WHITE)
        checkbox_rect = pygame.Rect(70, 580, 20, 20)

        pygame.draw.rect(self.screen, Constants.WHITE, checkbox_rect, 2)
        if hide_help:
            pygame.draw.rect(self.screen, Constants.WHITE, checkbox_rect.inflate(-8, -8))

        self.screen.blit(checkbox_text, (100, 575))

    def draw_game(self, game_state: GameState) -> None:
        """绘制游戏主界面"""
        # 绘制游戏区域背景
        pygame.draw.rect(self.screen, Constants.BLACK, (0, 0, Constants.GAME_AREA_WIDTH, Constants.SCREEN_HEIGHT))

        # 绘制网格和方块
        self._draw_grid()
        self._draw_blocks(game_state.grid)

        # 绘制当前方块
        game_state.current_tetrimino.draw(self.screen, self.pattern_img)

        # 绘制分数和侧边栏
        self._draw_score(game_state.score)
        self._draw_high_score(game_state.score)
        self._draw_sidebar(game_state)

        # 根据需要绘制暂停或游戏结束画面
        if game_state.paused:
            self._draw_paused()
        elif game_state.game_over:
            self._draw_game_over()

    def _draw_grid(self) -> None:
        """绘制网格线"""
        for x in range(0, Constants.GAME_AREA_WIDTH, Constants.BLOCK_SIZE):
            pygame.draw.line(self.screen, Constants.GRAY, (x, 0), (x, Constants.SCREEN_HEIGHT))
        for y in range(0, Constants.SCREEN_HEIGHT, Constants.BLOCK_SIZE):
            pygame.draw.line(self.screen, Constants.GRAY, (0, y), (Constants.GAME_AREA_WIDTH, y))

    def _draw_blocks(self, grid: List[List[int]]) -> None:
        """绘制已固定的方块"""
        for y in range(Constants.GRID_HEIGHT):
            for x in range(Constants.GRID_WIDTH):
                if grid[y][x]:
                    # 绘制底色
                    pygame.draw.rect(self.screen, grid[y][x],
                                     (x * Constants.BLOCK_SIZE, y * Constants.BLOCK_SIZE,
                                      Constants.BLOCK_SIZE, Constants.BLOCK_SIZE))

                    # 叠加图案（如果图片加载成功）
                    if self.pattern_img:
                        self.screen.blit(self.pattern_img,
                                         (x * Constants.BLOCK_SIZE, y * Constants.BLOCK_SIZE))

                    # 绘制边框
                    pygame.draw.rect(self.screen, Constants.BLACK,
                                     (x * Constants.BLOCK_SIZE, y * Constants.BLOCK_SIZE,
                                      Constants.BLOCK_SIZE, Constants.BLOCK_SIZE), 1)

    def _draw_score(self, score: int) -> None:
        """绘制当前得分"""
        font = pygame.font.SysFont("Microsoft YaHei", 24)
        score_text = font.render(f"得分: {score}", True, Constants.WHITE)
        self.screen.blit(score_text, (10, 10))

    def _draw_high_score(self, current_score: int) -> None:
        """绘制最高分"""
        high_score = self._get_high_score(current_score)
        font = pygame.font.SysFont("Microsoft YaHei", 24)
        high_score_text = font.render(f"最高: {high_score}", True, Constants.WHITE)
        self.screen.blit(high_score_text, (10, 40))

    def _get_high_score(self, current_score: int) -> int:
        """获取并更新最高分"""
        try:
            with open(Constants.HIGH_SCORE_FILE, "r") as file:
                high_score = int(file.read())
        except (FileNotFoundError, ValueError):
            high_score = 0

        if current_score > high_score:
            try:
                with open(Constants.HIGH_SCORE_FILE, "w") as file:
                    file.write(str(current_score))
                high_score = current_score
            except IOError as e:
                print(f"无法保存最高分: {e}")

        return high_score

    def _draw_sidebar(self, game_state: GameState) -> None:
        """绘制侧边栏"""
        # 侧边栏背景
        sidebar_rect = pygame.Rect(Constants.GAME_AREA_WIDTH, 0, Constants.SIDEBAR_WIDTH, Constants.SCREEN_HEIGHT)
        pygame.draw.rect(self.screen, Constants.DARK_GRAY, sidebar_rect)

        # 绘制标题
        font = pygame.font.SysFont("Microsoft YaHei", 20)
        title_text = font.render("游戏设置", True, Constants.WHITE)
        self.screen.blit(title_text,
                         (Constants.GAME_AREA_WIDTH + (Constants.SIDEBAR_WIDTH - title_text.get_width()) // 2, 20))

        # 绘制下一个方块提示
        next_text = font.render("下一个:", True, Constants.WHITE)
        self.screen.blit(next_text,
                         (Constants.GAME_AREA_WIDTH + (Constants.SIDEBAR_WIDTH - next_text.get_width()) // 2, 60))

        # 绘制下一个方块预览
        if game_state.next_tetrimino:
            preview_size = Constants.BLOCK_SIZE * 0.7
            preview_x = Constants.GAME_AREA_WIDTH + (
                    Constants.SIDEBAR_WIDTH - len(game_state.next_tetrimino.shape[0]) * preview_size) // 2
            preview_y = 100

            # 绘制预览背景
            preview_width = len(game_state.next_tetrimino.shape[0]) * preview_size
            preview_height = len(game_state.next_tetrimino.shape) * preview_size
            pygame.draw.rect(self.screen, Constants.LIGHT_GRAY,
                             (preview_x - 5, preview_y - 5, preview_width + 10, preview_height + 10))

            # 绘制方块
            for row in range(len(game_state.next_tetrimino.shape)):
                for col in range(len(game_state.next_tetrimino.shape[row])):
                    if game_state.next_tetrimino.shape[row][col]:
                        pygame.draw.rect(self.screen, game_state.next_tetrimino.color,
                                         (preview_x + col * preview_size,
                                          preview_y + row * preview_size,
                                          preview_size, preview_size))
                        pygame.draw.rect(self.screen, Constants.BLACK,
                                         (preview_x + col * preview_size,
                                          preview_y + row * preview_size,
                                          preview_size, preview_size), 1)

        # 绘制音乐开关
        music_text = font.render("背景音乐:", True, Constants.WHITE)
        self.screen.blit(music_text, (Constants.GAME_AREA_WIDTH + 10, 200))

        music_btn_rect = pygame.Rect(Constants.GAME_AREA_WIDTH + Constants.SIDEBAR_WIDTH - 50, 240, 40, 25)
        pygame.draw.rect(self.screen, Constants.GREEN if self.settings.music_enabled else Constants.RED, music_btn_rect)
        btn_text = font.render("开" if self.settings.music_enabled else "关", True, Constants.WHITE)
        self.screen.blit(btn_text, (music_btn_rect.x + (music_btn_rect.width - btn_text.get_width()) // 2,
                                    music_btn_rect.y + (music_btn_rect.height - btn_text.get_height()) // 2))

        # 绘制音效开关
        sound_text = font.render("游戏音效:", True, Constants.WHITE)
        self.screen.blit(sound_text, (Constants.GAME_AREA_WIDTH + 10, 270))

        sound_btn_rect = pygame.Rect(Constants.GAME_AREA_WIDTH + Constants.SIDEBAR_WIDTH - 50, 310, 40, 25)
        pygame.draw.rect(self.screen, Constants.GREEN if self.settings.sound_enabled else Constants.RED, sound_btn_rect)
        btn_text = font.render("开" if self.settings.sound_enabled else "关", True, Constants.WHITE)
        self.screen.blit(btn_text, (sound_btn_rect.x + (sound_btn_rect.width - btn_text.get_width()) // 2,
                                    sound_btn_rect.y + (sound_btn_rect.height - btn_text.get_height()) // 2))

        # 绘制灵敏度调节滑块
        self._draw_sensitivity_slider()

        # 绘制技能冷却条
        self._draw_skill_cooldown(game_state.last_skill_time)

    def _draw_sensitivity_slider(self) -> None:
        """绘制灵敏度调节滑块"""
        font = pygame.font.SysFont("Microsoft YaHei", 18)
        sens_text = font.render("移动灵敏度:", True, Constants.WHITE)
        self.screen.blit(sens_text, (Constants.GAME_AREA_WIDTH , 340))

        # 滑块轨道
        slider_x = Constants.GAME_AREA_WIDTH + 20
        slider_y = 380
        slider_width = Constants.SIDEBAR_WIDTH - 40
        slider_height = 10
        pygame.draw.rect(self.screen, Constants.LIGHT_GRAY, (slider_x, slider_y, slider_width, slider_height))

        # 计算滑块位置 (从最小延迟到最大延迟)
        min_delay = Constants.MIN_REPEAT_DELAY
        max_delay = Constants.MAX_REPEAT_DELAY
        current_delay = self.settings.repeat_delay

        # 计算滑块位置 (反向关系: 延迟越小，滑块越靠右)
        slider_pos = slider_x + ((max_delay - current_delay) / (max_delay - min_delay)) * slider_width

        # 确保滑块不会超出轨道
        slider_pos = max(slider_x, min(slider_x + slider_width, slider_pos))

        # 绘制滑块
        slider_rect = pygame.Rect(slider_pos - 5, slider_y - 5, 10, 20)
        pygame.draw.rect(self.screen, Constants.WHITE, slider_rect)

        # 显示当前延迟值
        delay_text = font.render(f"{current_delay}ms", True, Constants.WHITE)
        self.screen.blit(delay_text, (slider_x + (slider_width - delay_text.get_width()) // 2, slider_y + 20))

    def _draw_skill_cooldown(self, last_skill_time: float) -> None:
        """绘制技能冷却条"""
        current_time = time.time()
        elapsed = current_time - last_skill_time
        cooldown_ratio = min(1.0, elapsed / Constants.SKILL_COOLDOWN)

        # 冷却条背景
        bar_width = 80
        bar_height = 20
        bar_x = Constants.GAME_AREA_WIDTH + (Constants.SIDEBAR_WIDTH - bar_width) // 2
        bar_y = Constants.SCREEN_HEIGHT - 100  # 放在侧边栏底部

        # 绘制技能图标
        font = pygame.font.SysFont("Microsoft YaHei", 20)
        skill_text = font.render("坦克碾压", True, Constants.WHITE)
        self.screen.blit(skill_text, (bar_x, bar_y - 30))

        # 冷却条背景
        pygame.draw.rect(self.screen, Constants.GRAY, (bar_x, bar_y, bar_width, bar_height))

        # 冷却进度
        fill_width = int(bar_width * cooldown_ratio)
        if cooldown_ratio < 1.0:
            color = Constants.RED
            # 显示剩余时间
            remaining = int(Constants.SKILL_COOLDOWN - elapsed)
            time_text = font.render(f"{remaining}s", True, Constants.WHITE)
            self.screen.blit(time_text, (bar_x + bar_width // 2 - time_text.get_width() // 2, bar_y + bar_height + 5))
        else:
            color = Constants.GREEN
            ready_text = font.render("就绪", True, Constants.WHITE)
            self.screen.blit(ready_text, (bar_x + bar_width // 2 - ready_text.get_width() // 2, bar_y + bar_height + 5))

        pygame.draw.rect(self.screen, color, (bar_x, bar_y, fill_width, bar_height))
        pygame.draw.rect(self.screen, Constants.WHITE, (bar_x, bar_y, bar_width, bar_height), 2)

    def _draw_paused(self) -> None:
        """绘制暂停画面"""
        font = pygame.font.SysFont("Microsoft YaHei", 48)
        paused_text = font.render("游戏暂停", True, Constants.WHITE)
        self.screen.blit(paused_text, (Constants.GAME_AREA_WIDTH // 4, Constants.SCREEN_HEIGHT // 2))

    def _draw_game_over(self) -> None:
        """绘制游戏结束画面"""
        font = pygame.font.SysFont("Microsoft YaHei", 48)
        font2 = pygame.font.SysFont("Microsoft YaHei", 24)
        game_over_text = font.render("游戏结束", True, Constants.WHITE)
        restart_text = font2.render("按R重新开始", True, Constants.WHITE)
        quit_text = font2.render("按ESC退出", True, Constants.WHITE)
        self.screen.blit(game_over_text, (Constants.GAME_AREA_WIDTH // 4 - 20, Constants.SCREEN_HEIGHT // 2 - 120))
        self.screen.blit(restart_text, (Constants.GAME_AREA_WIDTH // 4 + 10, Constants.SCREEN_HEIGHT // 2))
        self.screen.blit(quit_text, (Constants.GAME_AREA_WIDTH // 4 + 15, Constants.SCREEN_HEIGHT // 2 + 60))


class GameController:
    """游戏控制器，管理游戏流程和用户输入"""

    def __init__(self):
        self.screen = pygame.display.set_mode((Constants.SCREEN_WIDTH, Constants.SCREEN_HEIGHT))
        pygame.display.set_caption("北理工方块")
        self.settings = GameSettings()
        self.renderer = GameRenderer(self.screen, self.settings)
        self.game_state = GameState(self.settings)
        self.clock = pygame.time.Clock()

    def run(self) -> None:
        """运行游戏主循环"""
        while True:
            if not self._show_start_screen():
                break

            self.game_state.reset()
            if not self._run_game_loop():
                break

            # 尝试重新播放背景音乐
            try:
                if self.settings.music_enabled:
                    pygame.mixer.music.play(-1, 0.0)
            except Exception as e:
                print(f"播放音乐失败: {e}")

    def _show_start_screen(self) -> bool:
        """显示开始界面并返回是否继续游戏"""
        if not self.settings.show_help:
            return True

        hide_help = False
        while True:
            self.renderer.draw_start_screen(hide_help)
            pygame.display.flip()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        self.settings.show_help = not hide_help
                        self.settings.save_settings(hide_help)
                        return True
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        sys.exit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_pos = pygame.mouse.get_pos()
                    if 70 <= mouse_pos[0] <= 90 and 560 <= mouse_pos[1] <= 590:  # 复选框区域
                        hide_help = not hide_help

            self.clock.tick(30)

    def _run_game_loop(self) -> bool:
        """运行游戏主循环并返回是否重新开始"""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()

                self._handle_event(event)

            # 更新游戏状态
            self.game_state.update()

            # 渲染游戏
            self.renderer.draw_game(self.game_state)
            pygame.display.flip()

            # 处理游戏结束后的等待
            if self.game_state.game_over:
                return self._wait_after_game_over()

            self.clock.tick(30)

    def _handle_event(self, event: pygame.event.Event) -> None:
        """处理游戏事件"""
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                pygame.quit()
                sys.exit()
            elif event.key == pygame.K_r:
                self.game_state.reset()
            elif event.key == pygame.K_RETURN:
                self.game_state.paused = not self.game_state.paused
            elif event.key == pygame.K_h:
                os.remove(Constants.SETTINGS_FILE)
            elif event.key == pygame.K_s:
                with open(Constants.HIGH_SCORE_FILE,'w') as f:
                    f.write("0")# 重置最高分
            elif event.key == pygame.K_f:
                if not self.game_state.paused:
                    self.game_state.clear_last_three_rows()
            elif not self.game_state.paused:
                if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN]:
                    self.game_state.held_keys[event.key] = True
                    self.game_state.last_move_time[event.key] = pygame.time.get_ticks()
                    # 立即响应第一次按键
                    if event.key == pygame.K_LEFT:
                        self.game_state.current_tetrimino.move(self.game_state.grid, -1, 0)
                    elif event.key == pygame.K_RIGHT:
                        self.game_state.current_tetrimino.move(self.game_state.grid, 1, 0)
                    elif event.key == pygame.K_DOWN:
                        self.game_state.current_tetrimino.move(self.game_state.grid, 0, 1)
                elif event.key == pygame.K_UP:
                    self.game_state.current_tetrimino.rotate(self.game_state.grid, self.settings)

        elif event.type == pygame.KEYUP:
            if event.key in [pygame.K_LEFT, pygame.K_RIGHT, pygame.K_DOWN]:
                self.game_state.held_keys[event.key] = False

        # 处理侧边栏按钮点击
        elif event.type == pygame.MOUSEBUTTONDOWN:
            mouse_pos = pygame.mouse.get_pos()
            if Constants.GAME_AREA_WIDTH <= mouse_pos[0] <= Constants.SCREEN_WIDTH:  # 点击在侧边栏
                # 检查是否点击了音乐按钮
                if (Constants.GAME_AREA_WIDTH + Constants.SIDEBAR_WIDTH - 50 <= mouse_pos[
                    0] <= Constants.SCREEN_WIDTH and
                        240 <= mouse_pos[1] <= 265):
                    self.settings.toggle_music()
                # 检查是否点击了音效按钮
                elif (Constants.GAME_AREA_WIDTH + Constants.SIDEBAR_WIDTH - 50 <= mouse_pos[
                    0] <= Constants.SCREEN_WIDTH and
                      310 <= mouse_pos[1] <= 335):
                    self.settings.toggle_sound()
                # 检查是否点击了灵敏度滑块
                elif (Constants.GAME_AREA_WIDTH + 20 <= mouse_pos[0] <= Constants.SCREEN_WIDTH - 20 and
                      375 <= mouse_pos[1] <= 395):  # 滑块区域
                    self.renderer.slider_dragging = True
                    self._update_sensitivity(mouse_pos[0])

        elif event.type == pygame.MOUSEBUTTONUP:
            self.renderer.slider_dragging = False

        elif event.type == pygame.MOUSEMOTION:
            if self.renderer.slider_dragging:
                self._update_sensitivity(event.pos[0])

        # 处理持续按键
        elif event.type == pygame.KEYUP and not self.game_state.paused:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_DOWN]:
                self.game_state.current_tetrimino.move(self.game_state.grid, 0, 1)

    def _update_sensitivity(self, mouse_x: int) -> None:
        """更新灵敏度设置"""
        # 计算滑块位置对应的延迟值
        slider_x = Constants.GAME_AREA_WIDTH + 20
        slider_width = Constants.SIDEBAR_WIDTH - 40

        # 将鼠标位置转换为滑块位置 (限制在轨道范围内)
        pos = max(slider_x, min(slider_x + slider_width, mouse_x))

        # 计算延迟值 (反向关系: 滑块越靠右，延迟越小)
        ratio = (pos - slider_x) / slider_width
        min_delay = Constants.MIN_REPEAT_DELAY
        max_delay = Constants.MAX_REPEAT_DELAY
        new_delay = max_delay - ratio * (max_delay - min_delay)

        # 设置新的延迟值
        self.settings.set_repeat_delay(int(new_delay))

        # 保存设置
        self.settings.save_settings(not self.settings.show_help)

    def _wait_after_game_over(self) -> bool:
        """游戏结束后等待玩家输入并返回是否重新开始"""
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:  # R键重新开始
                        return True
                    elif event.key == pygame.K_ESCAPE:  # ESC键退出
                        pygame.quit()
                        sys.exit()

            self.clock.tick(30)


if __name__ == '__main__':
    game = GameController()
    game.run()