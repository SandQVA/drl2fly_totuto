# -*- coding: utf-8 -*-
"""
Created on Tue Jun 11 16:22:26 2019

@author: andrea
"""


import torch
import torch.nn.functional as F


from utils import ReplayMemory, update_targets
from networks import Actor, Critic


class Model:
    
    def __init__(self, device, state_size, action_size, folder, config):
        
        
        self.folder = folder
        self.config = config
        self.device = device
        self.memory = ReplayMemory(self.config["MEMORY_CAPACITY"])

        self.state_size = state_size
        self.action_size = action_size
        
        self.critic = Critic(self.state_size, self.action_size, self.device, self.config)
        self.actor = Actor(self.state_size, self.action_size, self.device, self.config)
        
    
    def select_action(self,state):
        action = self.actor.select_action(state)
        return action


    def optimize(self):
        
        if len(self.memory) < self.config["BATCH_SIZE"]:
            return None, None

        transitions = self.memory.sample(self.config["BATCH_SIZE"])
        batch = list(zip(*transitions))

        # Divide memory into different tensors
        states = torch.FloatTensor(batch[0]).to(self.device)
        actions = torch.FloatTensor(batch[1]).to(self.device)
        rewards = torch.FloatTensor(batch[2]).unsqueeze(1).to(self.device)
        next_states = torch.FloatTensor(batch[3]).to(self.device)
        done = torch.FloatTensor(batch[4]).unsqueeze(1).to(self.device)

        # Compute Q(s,a) using critic network
        current_Q = self.critic(states, actions)

        # Compute deterministic next state action using actor target network
        next_actions = self.actor.target(next_states)

        # Compute next state values at t+1 using target critic network
        target_Q = self.critic.target(next_states, next_actions).detach()
        # Compute expected state action values y[i]= r[i] + Q'(s[i+1], a[i+1])
        target_Q = rewards + done*self.config["GAMMA"]*target_Q

        # Critic loss by mean squared error
        loss_critic = F.mse_loss(current_Q, target_Q)

        # Optimize the critic network
        self.critic.update(loss_critic)

        # Optimize actor
        loss_actor = -self.critic(states, self.actor(states)).mean()
        self.actor.update(loss_actor)

        # Soft parameter update
        update_targets(self.critic.target_nn, self.critic.nn, self.config["TAU"])
        update_targets(self.actor.target_nn, self.actor.nn, self.config["TAU"])

        return loss_actor.item(), loss_critic.item()

    def evaluate(self,environement, n_ep=10):
        rewards = []
        try:
            for i in range(n_ep):
                print('Episode number',i+1,'out of',n_ep,'keep waiting...')
                state = environement.reset()
                reward = 0
                done = False
                steps = 0
                while not done and steps < self.config["MAX_STEPS"]:
                    action = self.select_action(state)
                    state, r, done = environement.step(action)
                    reward += r
                    steps += 1
                rewards.append(reward)
                print('Episode reward:',reward)
        except KeyboardInterrupt:
            pass
        if rewards:
            score = sum(rewards)/len(rewards)
        else:
            score = 0
        
        return score
    
        
    def save(self):
        self.actor.save(self.folder)
        self.critic.save(self.folder)
        
        
        
    def load(self):
        try:
            self.actor.load(self.folder)
            self.critic.load(self.folder)
        except FileNotFoundError:
            raise Exception("No model has been saved !") from None