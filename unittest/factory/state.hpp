///////////////////////////////////////////////////////////////////////////////
// BSD 3-Clause License
//
// Copyright (C) 2018-2020, LAAS-CNRS, University of Edinburgh
// Copyright note valid unless otherwise stated in individual files.
// All rights reserved.
///////////////////////////////////////////////////////////////////////////////

#include <pinocchio/parsers/urdf.hpp>
#include <pinocchio/parsers/sample-models.hpp>
#include <example-robot-data/path.hpp>

#include "crocoddyl/core/state-base.hpp"
#include "crocoddyl/core/states/euclidean.hpp"
#include "crocoddyl/multibody/states/multibody.hpp"
#include "crocoddyl/core/numdiff/state.hpp"
#include "crocoddyl/core/utils/exception.hpp"

#include "pinocchio_model.hpp"

#ifndef CROCODDYL_STATE_FACTORY_HPP_
#define CROCODDYL_STATE_FACTORY_HPP_

namespace crocoddyl {
namespace unittest {

struct StateModelTypes {
  enum Type {
    StateVector,
    StateMultibody_TalosArm,
    StateMultibody_HyQ,
    StateMultibody_Talos,
    StateMultibody_RandomHumanoid,
    NbStateModelTypes
  };
  static std::vector<Type> init_all() {
    std::vector<Type> v;
    v.clear();
    for (int i = 0; i < NbStateModelTypes; ++i) {
      v.push_back((Type)i);
    }
    return v;
  }
  static const std::vector<Type> all;
};
const std::vector<StateModelTypes::Type> StateModelTypes::all(StateModelTypes::init_all());

std::ostream& operator<<(std::ostream& os, StateModelTypes::Type type) {
  switch (type) {
    case StateModelTypes::StateVector:
      os << "StateVector";
      break;
    case StateModelTypes::StateMultibody_TalosArm:
      os << "StateMultibody_TalosArm";
      break;
    case StateModelTypes::StateMultibody_HyQ:
      os << "StateMultibody_HyQ";
      break;
    case StateModelTypes::StateMultibody_Talos:
      os << "StateMultibody_Talos";
      break;
    case StateModelTypes::StateMultibody_RandomHumanoid:
      os << "StateMultibody_RandomHumanoid";
      break;
    case StateModelTypes::NbStateModelTypes:
      os << "NbStateModelTypes";
      break;
    default:
      break;
  }
  return os;
}

class StateModelFactory {
 public:
  EIGEN_MAKE_ALIGNED_OPERATOR_NEW

  explicit StateModelFactory() {}
  ~StateModelFactory() {}

  boost::shared_ptr<crocoddyl::StateAbstract> create(StateModelTypes::Type state_type) {
    boost::shared_ptr<pinocchio::Model> model;
    boost::shared_ptr<crocoddyl::StateAbstract> state;
    switch (state_type) {
      case StateModelTypes::StateVector:
        state = boost::make_shared<crocoddyl::StateVector>(80);
        break;
      case StateModelTypes::StateMultibody_TalosArm:
        model = PinocchioModelFactory(PinocchioModelTypes::TalosArm).create();
        state = boost::make_shared<crocoddyl::StateMultibody>(model);
        break;
      case StateModelTypes::StateMultibody_HyQ:
        model = PinocchioModelFactory(PinocchioModelTypes::HyQ).create();
        state = boost::make_shared<crocoddyl::StateMultibody>(model);
        break;
      case StateModelTypes::StateMultibody_Talos:
        model = PinocchioModelFactory(PinocchioModelTypes::Talos).create();
        state = boost::make_shared<crocoddyl::StateMultibody>(model);
        break;
      case StateModelTypes::StateMultibody_RandomHumanoid:
        model = PinocchioModelFactory(PinocchioModelTypes::RandomHumanoid).create();
        state = boost::make_shared<crocoddyl::StateMultibody>(model);
        break;
      default:
        throw_pretty(__FILE__ ": Wrong StateModelTypes::Type given");
        break;
    }
    return state;
  }

 private:
};

}  // namespace unittest
}  // namespace crocoddyl

#endif  // CROCODDYL_STATE_FACTORY_HPP_
