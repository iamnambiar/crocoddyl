///////////////////////////////////////////////////////////////////////////////
// BSD 3-Clause License
//
// Copyright (C) 2019-2023, LAAS-CNRS, University of Edinburgh,
//                          Heriot-Watt University
// Copyright note valid unless otherwise stated in individual files.
// All rights reserved.
///////////////////////////////////////////////////////////////////////////////

#ifndef CROCODDYL_MULTIBODY_IMPULSES_IMPULSE_6D_HPP_
#define CROCODDYL_MULTIBODY_IMPULSES_IMPULSE_6D_HPP_

#include <pinocchio/spatial/motion.hpp>
#include <pinocchio/multibody/data.hpp>

#include "crocoddyl/multibody/fwd.hpp"
#include "crocoddyl/multibody/impulse-base.hpp"

namespace crocoddyl {

template <typename _Scalar>
class ImpulseModel6DTpl : public ImpulseModelAbstractTpl<_Scalar> {
 public:
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ImpulseModelAbstractTpl<Scalar> Base;
  typedef ImpulseData6DTpl<Scalar> Data;
  typedef StateMultibodyTpl<Scalar> StateMultibody;
  typedef ImpulseDataAbstractTpl<Scalar> ImpulseDataAbstract;
  typedef typename MathBase::Vector2s Vector2s;
  typedef typename MathBase::Vector3s Vector3s;
  typedef typename MathBase::VectorXs VectorXs;
  typedef typename MathBase::MatrixXs MatrixXs;
  typedef typename MathBase::Matrix3s Matrix3s;

  /**
   * @brief Initialize the 6d impulse model
   *
   * @param[in] state  State of the multibody system
   * @param[in] id     Reference frame id of the impulse
   * @param[in] type   Type of impulse (default LOCAL)
   */
  ImpulseModel6DTpl(boost::shared_ptr<StateMultibody> state, const pinocchio::FrameIndex id,
                    const pinocchio::ReferenceFrame type = pinocchio::ReferenceFrame::LOCAL);
  virtual ~ImpulseModel6DTpl();

  /**
   * @brief Compute the 3d impulse Jacobian
   *
   * @param[in] data  3d impulse data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   */
  virtual void calc(const boost::shared_ptr<ImpulseDataAbstract>& data, const Eigen::Ref<const VectorXs>& x);

  /**
   * @brief Compute the derivatives of the 3d impulse holonomic constraint
   *
   * @param[in] data  3d impulse data
   * @param[in] x     State point \f$\mathbf{x}\in\mathbb{R}^{ndx}\f$
   */
  virtual void calcDiff(const boost::shared_ptr<ImpulseDataAbstract>& data, const Eigen::Ref<const VectorXs>& x);

  /**
   * @brief Convert the force into a stack of spatial forces
   *
   * @param[in] data   3d impulse data
   * @param[in] force  3d impulse
   */
  virtual void updateForce(const boost::shared_ptr<ImpulseDataAbstract>& data, const VectorXs& force);

  /**
   * @brief Create the 3d impulse data
   */
  virtual boost::shared_ptr<ImpulseDataAbstract> createData(pinocchio::DataTpl<Scalar>* const data);

  /**
   * @brief Print relevant information of the 6d impulse model
   *
   * @param[out] os  Output stream object
   */
  virtual void print(std::ostream& os) const;

 protected:
  using Base::id_;
  using Base::state_;
  using Base::type_;
};

template <typename _Scalar>
struct ImpulseData6DTpl : public ImpulseDataAbstractTpl<_Scalar> {
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW
  typedef _Scalar Scalar;
  typedef MathBaseTpl<Scalar> MathBase;
  typedef ImpulseDataAbstractTpl<Scalar> Base;
  typedef typename MathBase::Matrix3s Matrix3s;
  typedef typename MathBase::Matrix6xs Matrix6xs;
  typedef typename MathBase::MatrixXs MatrixXs;
  typedef typename pinocchio::SE3Tpl<Scalar> SE3;
  typedef typename pinocchio::MotionTpl<Scalar> Motion;
  typedef typename pinocchio::ForceTpl<Scalar> Force;

  template <template <typename Scalar> class Model>
  ImpulseData6DTpl(Model<Scalar>* const model, pinocchio::DataTpl<Scalar>* const data)
      : Base(model, data),
        lwaMl(SE3::Identity()),
        v0(Motion::Zero()),
        f_local(Force::Zero()),
        dv0_local_dq(6, model->get_state()->get_nv()),
        fJf(6, model->get_state()->get_nv()),
        v_partial_dq(6, model->get_state()->get_nv()),
        v_partial_dv(6, model->get_state()->get_nv()),
        fJf_df(6, model->get_state()->get_nv()) {
    frame = model->get_id();
    jMf = model->get_state()->get_pinocchio()->frames[model->get_id()].placement;
    fXj = jMf.inverse().toActionMatrix();
    fJf.setZero();
    v_partial_dq.setZero();
    v_partial_dv.setZero();
    vv_skew.setZero();
    vw_skew.setZero();
    vv_world_skew.setZero();
    vw_world_skew.setZero();
    fv_skew.setZero();
    fw_skew.setZero();
    fJf_df.setZero();
  }

  using Base::df_dx;
  using Base::dv0_dq;
  using Base::f;
  using Base::frame;
  using Base::fXj;
  using Base::Jc;
  using Base::jMf;
  using Base::pinocchio;

  SE3 lwaMl;
  Motion v0;
  Force f_local;
  Matrix6xs dv0_local_dq;
  Matrix6xs fJf;
  Matrix6xs v_partial_dq;
  Matrix6xs v_partial_dv;
  Matrix3s vv_skew;
  Matrix3s vw_skew;
  Matrix3s vv_world_skew;
  Matrix3s vw_world_skew;
  Matrix3s fv_skew;
  Matrix3s fw_skew;
  MatrixXs fJf_df;
};

}  // namespace crocoddyl

/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
/* --- Details -------------------------------------------------------------- */
#include "crocoddyl/multibody/impulses/impulse-6d.hxx"

#endif  // CROCODDYL_MULTIBODY_IMPULSES_IMPULSE_6D_HPP_
