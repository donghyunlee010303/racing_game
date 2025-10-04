#!/usr/bin/env python3
"""Simple Pygame car racing game with keyboard controls."""

import random
import pygame
import sys
from dataclasses import dataclass
from typing import Optional, List, Tuple


@dataclass(frozen=True)
class GameConfig:
    width: int = 400
    height: int = 600
    lane_count: int = 3
    border_x: int = 60
    lane_marker_length: int = 48
    lane_marker_gap: int = 80
    fps: int = 60


class Car:
    def __init__(self, x: int, y: int, width: int, height: int, color: Tuple[int, int, int]):
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)
    
    def update(self, dx: int, dy: int = 0):
        self.x += dx
        self.y += dy
        self.rect.x = self.x - self.width // 2
        self.rect.y = self.y - self.height // 2
    
    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, self.color, self.rect)


class RacingGame:
    def __init__(self, config: Optional[GameConfig] = None) -> None:
        pygame.init()
        self.config = config or GameConfig()
        
        # 화면 설정
        self.screen = pygame.display.set_mode((self.config.width, self.config.height))
        pygame.display.set_caption("레이싱 게임")
        self.clock = pygame.time.Clock()
        
        # 색상 정의
        self.colors = {
            'road': (60, 60, 60),
            'grass': (34, 139, 34),
            'lane_marker': (255, 255, 255),
            'player_car': (255, 0, 0),
            'enemy_car': (0, 100, 255),
            'text': (255, 255, 255),
            'background': (0, 0, 0)
        }
        
        # 트랙 설정
        self.track_left = self.config.border_x
        self.track_right = self.config.width - self.config.border_x
        self.lane_width = (self.track_right - self.track_left) / self.config.lane_count
        
        # 게임 변수
        self.car_speed = 5
        self.road_scroll_speed = 3
        self.obstacle_speed = 3
        self.spawn_cooldown_range = (60, 120)  # 프레임 단위
        
        # 플레이어 차량
        car_width = int(self.lane_width * 0.6)
        car_height = 40
        car_x = self._lane_center(1)
        car_y = self.config.height - 80
        self.player_car = Car(car_x, car_y, car_width, car_height, self.colors['player_car'])
        
        # 장애물과 차선 마커
        self.obstacles: List[Car] = []
        self.lane_markers: List[Tuple[int, int]] = []  # (x, y) 좌표
        
        # 게임 상태
        self.score = 0.0
        self.spawn_timer = self._next_spawn_delay()
        self.running = True
        self.game_over = False
        
        # 차선 마커 초기화
        self._init_lane_markers()
        
        # 폰트 설정
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)

    def _init_lane_markers(self) -> None:
        """차선 마커 초기화"""
        for lane in range(1, self.config.lane_count):
            x = int(self.track_left + lane * self.lane_width)
            for y in range(-self.config.lane_marker_length, 
                          self.config.height + self.config.lane_marker_length, 
                          self.config.lane_marker_length + self.config.lane_marker_gap):
                self.lane_markers.append((x, y))

    def handle_events(self) -> None:
        """이벤트 처리"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_RETURN and self.game_over:
                    self._reset_game()
                elif event.key == pygame.K_ESCAPE:
                    self.running = False

    def update(self) -> None:
        """게임 상태 업데이트"""
        if not self.game_over:
            self._update_car()
            self._update_lane_markers()
            self._update_obstacles()
            self._maybe_spawn_obstacle()
            self._update_score()

    def _update_car(self) -> None:
        """플레이어 차량 업데이트"""
        keys = pygame.key.get_pressed()
        dx = 0
        
        if keys[pygame.K_LEFT] and not keys[pygame.K_RIGHT]:
            dx = -self.car_speed
        elif keys[pygame.K_RIGHT] and not keys[pygame.K_LEFT]:
            dx = self.car_speed

        if dx:
            new_x = self.player_car.x + dx
            # 트랙 경계 확인
            if (new_x - self.player_car.width // 2 >= self.track_left and 
                new_x + self.player_car.width // 2 <= self.track_right):
                self.player_car.update(dx)

    def _update_lane_markers(self) -> None:
        """차선 마커 업데이트"""
        for i, (x, y) in enumerate(self.lane_markers):
            new_y = y + self.road_scroll_speed
            if new_y > self.config.height:
                new_y = -self.config.lane_marker_length
            self.lane_markers[i] = (x, new_y)

    def _update_obstacles(self) -> None:
        """장애물 업데이트"""
        obstacles_to_remove = []
        
        for obstacle in self.obstacles:
            obstacle.update(0, self.obstacle_speed)
            
            # 화면 밖으로 나간 장애물 제거
            if obstacle.y > self.config.height:
                obstacles_to_remove.append(obstacle)
                continue
                
            # 충돌 검사
            if self._check_collision(obstacle):
                self._game_over()
                return
                
        # 제거할 장애물들 삭제
        for obstacle in obstacles_to_remove:
            self.obstacles.remove(obstacle)

    def _maybe_spawn_obstacle(self) -> None:
        """새 장애물 생성"""
        self.spawn_timer -= 1
        if self.spawn_timer <= 0:
            lane = random.randrange(self.config.lane_count)
            width = int(self.lane_width * 0.6)
            height = 50
            x = self._lane_center(lane)
            y = -height
            
            obstacle = Car(x, y, width, height, self.colors['enemy_car'])
            self.obstacles.append(obstacle)
            self.spawn_timer = self._next_spawn_delay()

    def _update_score(self) -> None:
        """점수 업데이트"""
        self.score += 1.0 / self.config.fps

    def draw(self) -> None:
        """화면 그리기"""
        # 배경 그리기
        self.screen.fill(self.colors['background'])
        
        # 잔디 지역 그리기
        pygame.draw.rect(self.screen, self.colors['grass'], 
                        (0, 0, self.track_left, self.config.height))
        pygame.draw.rect(self.screen, self.colors['grass'], 
                        (self.track_right, 0, self.config.width - self.track_right, self.config.height))
        
        # 도로 그리기
        pygame.draw.rect(self.screen, self.colors['road'], 
                        (self.track_left, 0, self.track_right - self.track_left, self.config.height))
        
        # 차선 마커 그리기
        for x, y in self.lane_markers:
            pygame.draw.rect(self.screen, self.colors['lane_marker'], 
                           (x - 3, y, 6, self.config.lane_marker_length))
        
        # 장애물 그리기
        for obstacle in self.obstacles:
            obstacle.draw(self.screen)
        
        # 플레이어 차량 그리기
        self.player_car.draw(self.screen)
        
        # 점수 표시
        score_text = self.small_font.render(f"Score: {self.score:.1f}", True, self.colors['text'])
        self.screen.blit(score_text, (10, 10))
        
        # 게임 오버 메시지
        if self.game_over:
            game_over_text = self.font.render("Crash!", True, self.colors['text'])
            restart_text = self.small_font.render("Press Enter to Resume", True, self.colors['text'])
            
            # 텍스트 중앙 정렬
            game_over_rect = game_over_text.get_rect(center=(self.config.width // 2, self.config.height // 2 - 20))
            restart_rect = restart_text.get_rect(center=(self.config.width // 2, self.config.height // 2 + 20))
            
            self.screen.blit(game_over_text, game_over_rect)
            self.screen.blit(restart_text, restart_rect)
        
        pygame.display.flip()

    # Helper methods ------------------------------------------------------
    def _lane_center(self, lane: int) -> float:
        return self.track_left + self.lane_width * (lane + 0.5)

    def _next_spawn_delay(self) -> int:
        return random.randint(*self.spawn_cooldown_range)

    def _check_collision(self, obstacle: Car) -> bool:
        return self.player_car.rect.colliderect(obstacle.rect)

    def _game_over(self) -> None:
        self.game_over = True

    def _reset_game(self) -> None:
        self.game_over = False
        self.obstacles.clear()
        self.score = 0.0
        self.spawn_timer = self._next_spawn_delay()
        
        # 플레이어 차량을 중앙으로 리셋
        car_x = self._lane_center(1)
        car_y = self.config.height - 80
        self.player_car.x = car_x
        self.player_car.y = car_y
        self.player_car.rect.x = car_x - self.player_car.width // 2
        self.player_car.rect.y = car_y - self.player_car.height // 2

    def run(self) -> None:
        """메인 게임 루프"""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(self.config.fps)
        
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    RacingGame().run()
