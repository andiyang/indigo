import time
import tensorflow as tf
import numpy as np


class Reinforce(object):
    def __init__(self, **params):
        self.state_dim = params['state_dim']
        self.action_cnt = params['action_cnt']

        # epsilon-greedy exploration probability
        self.explore_prob = 0.5
        self.init_explore_prob = 0.5
        self.final_explore_prob = 0.0
        self.anneal_steps = 10000

        self.train_iter = 0

        self.reward_discount = 0.99

        self.build_tf_graph()

    def build_tf_graph(self):
        self.session = tf.Session()
        self.build_policy_network()
        self.build_loss()
        self.build_gradients()

        # initialize variables
        self.session.run(tf.global_variables_initializer())

    def build_policy_network(self):
        self.state = tf.placeholder(tf.float32, [None, self.state_dim])
        W1 = tf.get_variable('W1', [self.state_dim, 5],
                             initializer=tf.random_normal_initializer())
        b1 = tf.get_variable('b1', [5],
                             initializer=tf.constant_initializer(0.0))
        h1 = tf.nn.relu(tf.matmul(self.state, W1) + b1)

        W2 = tf.get_variable('W2', [5, self.action_cnt],
                             initializer=tf.random_normal_initializer())
        b2 = tf.get_variable('b2', [self.action_cnt],
                             initializer=tf.constant_initializer(0.0))
        self.action_scores = tf.matmul(h1, W2) + b2
        self.predicted_action = tf.multinomial(self.action_scores, 1)
        self.network_vars = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)

    def build_loss(self):
        self.taken_action = tf.placeholder(tf.int32, (None,))

        # create nodes to compute cross entropy and regularization loss
        self.ce_loss = tf.nn.sparse_softmax_cross_entropy_with_logits(
            labels=self.taken_action, logits=self.action_scores)
        self.ce_loss = tf.reduce_mean(self.ce_loss)

        self.reg_penalty = 0.001
        self.reg_loss = 0.0
        for x in self.network_vars:
            self.reg_loss += tf.nn.l2_loss(x)
        self.reg_loss *= self.reg_penalty

        self.loss = self.ce_loss + self.reg_loss

    def build_gradients(self):
        self.optimizer = tf.train.GradientDescentOptimizer(learning_rate=0.01)

        # create notes to compute gradients update used in REINFORCE
        self.gradients = self.optimizer.compute_gradients(self.loss)

        self.discounted_reward = tf.placeholder(tf.float32, (None,))
        for i, (grad, var) in enumerate(self.gradients):
            assert grad is not None
            self.gradients[i] = (self.discounted_reward * grad, var)

        # create notes to apply gradients
        self.train = self.optimizer.apply_gradients(self.gradients)

    def sample_action(self, state):
        # epsilon-greedy exploration
        if np.random.random() < self.explore_prob:
            action = np.random.randint(0, self.action_cnt)
            print 'random action', action
        else:
            state = np.array([state])
            action = self.session.run(self.predicted_action,
                                      {self.state: state})[0][0]
            print 'predicted action', action

        time.sleep(1)
        return 1

    def store_experience(self, experience):
        self.state_buf, self.action_buf, self.reward = experience
        assert len(self.state_buf) == len(self.action_buf)

    def anneal_exploration(self):
        ratio = float(self.anneal_steps - self.train_iter) / self.anneal_steps
        ratio = max(ratio, 0)
        self.explore_prob = self.final_explore_prob + ratio * (
                            self.init_explore_prob - self.final_explore_prob)

    def update_model(self):
        T = len(self.state_buf)

        for t in xrange(T-1):
            state = np.array(self.state_buf[t])[np.newaxis, :]
            action = np.array([self.action_buf[t]])
            reward_discount = pow(self.reward_discount, T-1-t)
            discounted_reward = np.array([reward_discount * self.reward])

            self.session.run(self.train, {
                self.state: state,
                self.taken_action: action,
                self.discounted_reward: discounted_reward
            })

        self.anneal_exploration()
        self.train_iter += 1