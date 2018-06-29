import numpy as np
from data import RunningDDPData, TerminalDDPData


class ConstrainedDDP:

  def __init__(self, dynamics, cost_manager, integrator, timeline):
    self.dynamics = dynamics
    self.cost_manager = cost_manager
    self.integrator = integrator
    self.timeline = timeline
    self.N = len(timeline) - 1

    # Allocation of data for all the DDP intervals
    self.intervals = []
    for k in range(self.N + 1):
      # Creating the dynamic and cost data
      ddata = self.dynamics.createData()
      if k == self.N:
        cdata = self.cost_manager.createTerminalData(ddata.n)
        self.intervals.append(TerminalDDPData(ddata, cdata))
      else:
        cdata = self.cost_manager.createRunningData(ddata.n, ddata.m)
        self.intervals.append(RunningDDPData(ddata, cdata))

    # Global variables for the DDP algorithm
    self.V = np.matrix(np.zeros(1))
    self.V_new = np.matrix(np.zeros(1))
    self.dV_exp = np.matrix(np.zeros(1))

    # Setting the time values of the running intervals
    for k in range(self.N):
      it = self.intervals[k]
      it.t0 = timeline[k]
      it.tf = timeline[k+1]

    # Defining the inital and terminal intervals
    self.terminal_interval = self.intervals[-1]
    self.initial_interval = self.intervals[0]

    self.total_cost = float('Inf')

    # Regularization
    self.mu = 1e-8

    # Lower and upper bound of iteration acceptance (line-search)
    self.change_lb = 0.
    self.change_ub = 100.

  def setInitalState(self, x0):
    """ Initializes the actual state of the dynamical system.

    :param x0: initial state vector (n-dimensional vector).
    """
    np.copyto(self.initial_interval.x, x0)

  def setInitialControl(self, U):
    """ Initializes the control sequences.

    :param U: initial control sequence (stack of m-dimensional vector).
    """
    assert len(U) == self.N, "Incompleted control sequence."
    for k in range(self.N):
      it = self.intervals[k]
      np.copyto(it.u, U[k])
      np.copyto(it.u_new, U[k])

  def init(self):
    """ Initializes the DDP algorithm

    It integrates the system's dynamics given an initial state, and a control sequences. This provides the initial nominal trajectory.
    """
    # Initializing the forward pass with the initial state
    it = self.initial_interval
    x0 = it.x
    np.copyto(it.x, x0)
    np.copyto(it.x_new, x0)
    self.V[0] = 0.

    # Integrate the system along the initial control sequences
    for k in range(self.N):
      # Getting the current DDP interval
      it = self.intervals[k]
      it_next = self.intervals[k+1]

      # Integrating the dynamics and updating the new state value
      dt = it.tf - it.t0
      x_next = self.integrator.integrate(self.dynamics, it.dynamics, it.x, it.u, dt)
      np.copyto(it_next.x, x_next)
      np.copyto(it_next.x_new, x_next)

      # Integrating the cost and updating the new value function
      self.V[0] += self.cost_manager.computeRunningCost(it.cost, it.x, it.u) * dt

    # Including the terminal state and cost
    it = self.terminal_interval
    it.x = self.intervals[self.N-1].x
    self.V[0] += self.cost_manager.computeTerminalCost(it.cost, it.x)

  def compute(self):
    """ Computes the DDP algorithm
    """
    alpha = 1.
    self.backwardPass(alpha)
    self.forwardPass(alpha)

  def backwardPass(self, alpha):
    """ Runs the forward pass of the DDP algorithm

    :param alpha: scaling factor of open-loop control modification (line-search strategy)
    """
    # Setting up the final value function as the terminal cost, so we proceed with
    # the backward sweep
    it = self.terminal_interval
    xf = it.x
    it.V, it.Vx, it.Vxx = self.cost_manager.computeTerminalTerms(it.cost, xf)

    # Setting up the initial cost value, and the expected reduction equals zero
    self.V[0] = it.V.copy()
    self.dV_exp[0] = 0.

    # Computing the regularization term
    muI = self.mu * np.eye(it.dynamics.n)

    # Running the backward sweep
    for k in range(self.N-1, -1, -1):
      it = self.intervals[k]
      it_next = self.intervals[k+1]
      cost_data = it.cost
      dyn_data = it.dynamics

      # Getting the state, control and step time of the interval
      x = it.x
      u = it.u
      dt = it.tf - it.t0

      # Computing the cost and its derivatives
      l, lx, lu, lxx, luu, lux = self.cost_manager.computeRunningTerms(cost_data, x, u)

      # Integrating the derivatives of the cost function
      # TODO we need to use the integrator class for this
      l *= dt
      lx *= dt
      lu *= dt
      lxx *= dt
      luu *= dt
      lux *= dt

      # Computing the dynamics and its derivatives
      _, fx, fu = self.dynamics.computeAllTerms(dyn_data, x, u)

      # Integrating the derivatives of the system dynamics
      # TODO we need to use the integrator class for this
      np.copyto(fx, fx * dt + np.eye(dyn_data.n))
      np.copyto(fu, fu * dt)

      # Getting the value function values of the next interval (prime interval)
      Vx_p = it_next.Vx
      Vxx_p = it_next.Vxx

      # Updating the Q derivatives. Note that this is Gauss-Newton step because
      # we neglect the Hessian, it's also called iLQR.
      np.copyto(it.Qx, lx + fx.T * Vx_p)
      np.copyto(it.Qu, lu + fu.T * Vx_p)
      np.copyto(it.Qxx, lxx + fx.T * Vxx_p * fx)
      np.copyto(it.Quu, luu + fu.T * Vxx_p * fu)
      np.copyto(it.Qux, lux + fu.T * Vxx_p * fx)

      # We apply a regularization on the Quu and Qux as Tassa.
      # This regularization is needed when the Hessian is not
      # positive-definitive or when the minimum is far and the
      # quadratic model is inaccurate
      np.copyto(it.Quu_r, it.Quu + fu.T * muI * fu)
      np.copyto(it.Qux_r, it.Qux + fu.T * muI * fx)

      # Computing the feedback and feedforward terms
      L_inv = np.linalg.inv(np.linalg.cholesky(it.Quu_r))
      Quu_inv = L_inv.T * L_inv
      np.copyto(it.K, - Quu_inv * it.Qux_r)
      np.copyto(it.j, - Quu_inv * it.Qu)

      # Computing the value function derivatives of this interval
      jt_Quu_j = 0.5 * it.j.T * it.Quu * it.j
      jt_Qu = it.j.T * it.Qu
      np.copyto(it.Vx, it.Qx + it.K.T * it.Quu * it.j + it.K.T * it.Qu + it.Qux.T * it.j)
      np.copyto(it.Vxx, it.Qxx + it.K.T * it.Quu * it.K + it.K.T * it.Qux + it.Qux.T * it.K)

      # Updating the local cost and expected reduction. The total values are used to check
      # the changes in the forward pass. This is method is explained in Tassa's PhD thesis
      self.V[0] += l
      self.dV_exp[0] += alpha * (alpha * jt_Quu_j + jt_Qu)

  def forwardPass(self, alpha):
    """ Runs the forward pass of the DDP algorithm

    :param alpha: scaling factor of open-loop control modification (line-search strategy)
    """
    # Initializing the forward pass with the initial state
    it = self.initial_interval
    it.x_new = it.x.copy()
    self.V_new = 0.

    # Integrate the system along the new trajectory
    for k in range(self.N):
      # Getting the current DDP interval
      it = self.intervals[k]
      it_next = self.intervals[k+1]

      # Computing the new control command
      np.copyto(it.u_new, it.u + alpha * it.j + it.K * (it.x_new - it.x))

      # Integrating the dynamics and updating the new state value
      dt = it.tf - it.t0
      np.copyto(it_next.x_new,
                self.integrator.integrate(self.dynamics, it.dynamics, it.x_new, it.u_new, dt))

      # Integrating the cost and updating the new value function
      # TODO we need to use the integrator class for this
      self.V_new += self.cost_manager.computeRunningCost(it.cost, it.x_new, it.u_new) * dt

    # Including the terminal cost
    it = self.terminal_interval
    it.x = self.intervals[self.N-1].x_new
    self.V_new += self.cost_manager.computeTerminalCost(it.cost, it.x)

    # Checking the changes
    z = (self.V_new - self.V) / self.dV_exp
    print z, self.V, self.V_new, self.dV_exp
    print "Expected Reduction:", -self.dV_exp[0, 0]
    print "Actual Reduction:", np.asscalar(self.V - self.V_new)
    print "Reduction Ratio", -np.asscalar(self.V - self.V_new) / self.dV_exp[0, 0]
    if z > self.change_lb and z < self.change_ub:
      # Accepting the new trajectory and control, defining them as nominal ones
      for k in range(self.N-1):
        it = self.intervals[k]
        np.copyto(it.u, it.u_new)
        np.copyto(it.x, it.x_new)

  # def getControlTrajectory(self):

  #   control_traj = np.matrix(np.zeros((self.model.m,self.N)))
  #   for k,it in enumerate(self.intervals[:-1]):
  #     control_traj[:,k] = it.u

  #   return control_traj

  # def getStateTrajectory(self):

  #   state_traj = np.matrix(np.zeros((self.model.n,self.N+1)))
  #   for k,it in enumerate(self.intervals[:-1]):
  #     state_traj[:,k] = it.x0

  #   state_traj[:,-1] = self.terminal_interval.x

  #   return state_traj
