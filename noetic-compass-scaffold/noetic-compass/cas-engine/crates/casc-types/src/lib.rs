//! Hindley-Milner-style type machinery for the CAS compiler.
//!
//! This crate provides reusable type variables, schemes, substitution,
//! unification, generalization, and instantiation. It is intentionally
//! narrower than a full language implementation: it models primitive CAS
//! value kinds plus function types, and is meant to be embedded by the
//! frontend rather than act as a parser or evaluator.

use std::collections::{HashMap, HashSet};

pub type TypeVarId = u32;

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum PrimitiveType {
    State,
    Drive,
    String,
    Fractal,
    Rpm,
    Relation,
    Program,
    Number,
    MetaSet,
    MetaSymbol,
    MetaAssertion,
    Any,
}

#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub enum MonoType {
    Var(TypeVarId),
    Primitive(PrimitiveType),
    Function(Vec<MonoType>, Box<MonoType>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Scheme {
    pub vars: Vec<TypeVarId>,
    pub ty: MonoType,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum InferenceError {
    OccursCheckFailed { var: TypeVarId, ty: MonoType },
    TypeMismatch { left: MonoType, right: MonoType },
}

#[derive(Debug, Clone, Default, PartialEq, Eq)]
pub struct Substitution {
    map: HashMap<TypeVarId, MonoType>,
}

impl Substitution {
    pub fn insert(&mut self, var: TypeVarId, ty: MonoType) {
        self.map.insert(var, ty);
    }

    pub fn apply(&self, ty: &MonoType) -> MonoType {
        match ty {
            MonoType::Var(var) => self
                .map
                .get(var)
                .map(|inner| self.apply(inner))
                .unwrap_or_else(|| MonoType::Var(*var)),
            MonoType::Primitive(kind) => MonoType::Primitive(kind.clone()),
            MonoType::Function(params, ret) => MonoType::Function(
                params.iter().map(|param| self.apply(param)).collect(),
                Box::new(self.apply(ret)),
            ),
        }
    }
}

#[derive(Debug, Clone, Default)]
pub struct TypeEnv {
    bindings: HashMap<String, Scheme>,
}

impl TypeEnv {
    pub fn insert(&mut self, name: impl Into<String>, scheme: Scheme) {
        self.bindings.insert(name.into(), scheme);
    }

    pub fn get(&self, name: &str) -> Option<&Scheme> {
        self.bindings.get(name)
    }

    fn free_type_vars(&self) -> HashSet<TypeVarId> {
        self.bindings
            .values()
            .flat_map(free_type_vars_scheme)
            .collect()
    }
}

#[derive(Debug, Clone, Default)]
pub struct InferCtx {
    next_var: TypeVarId,
    subst: Substitution,
}

impl InferCtx {
    pub fn fresh_var(&mut self) -> MonoType {
        let id = self.next_var;
        self.next_var += 1;
        MonoType::Var(id)
    }

    pub fn subst(&self) -> &Substitution {
        &self.subst
    }

    pub fn instantiate(&mut self, scheme: &Scheme) -> MonoType {
        let replacements: HashMap<TypeVarId, MonoType> = scheme
            .vars
            .iter()
            .copied()
            .map(|var| (var, self.fresh_var()))
            .collect();
        instantiate_type(&scheme.ty, &replacements)
    }

    pub fn generalize(&self, env: &TypeEnv, ty: &MonoType) -> Scheme {
        let ty = self.subst.apply(ty);
        let env_vars = env.free_type_vars();
        let vars = free_type_vars(&ty)
            .into_iter()
            .filter(|var| !env_vars.contains(var))
            .collect();
        Scheme { vars, ty }
    }

    pub fn unify(&mut self, left: &MonoType, right: &MonoType) -> Result<MonoType, InferenceError> {
        let left = self.subst.apply(left);
        let right = self.subst.apply(right);
        match (left, right) {
            (MonoType::Var(var), ty) | (ty, MonoType::Var(var)) => {
                self.bind(var, ty.clone())?;
                Ok(self.subst.apply(&ty))
            }
            (MonoType::Primitive(left), MonoType::Primitive(right)) if left == right => {
                Ok(MonoType::Primitive(left))
            }
            (
                MonoType::Function(left_params, left_ret),
                MonoType::Function(right_params, right_ret),
            ) => {
                if left_params.len() != right_params.len() {
                    return Err(InferenceError::TypeMismatch {
                        left: MonoType::Function(left_params, left_ret),
                        right: MonoType::Function(right_params, right_ret),
                    });
                }
                let params = left_params
                    .iter()
                    .zip(right_params.iter())
                    .map(|(l, r)| self.unify(l, r))
                    .collect::<Result<Vec<_>, _>>()?;
                let ret = self.unify(&left_ret, &right_ret)?;
                Ok(MonoType::Function(params, Box::new(ret)))
            }
            (left, right) => Err(InferenceError::TypeMismatch { left, right }),
        }
    }

    fn bind(&mut self, var: TypeVarId, ty: MonoType) -> Result<(), InferenceError> {
        if ty == MonoType::Var(var) {
            return Ok(());
        }
        if free_type_vars(&ty).contains(&var) {
            return Err(InferenceError::OccursCheckFailed { var, ty });
        }
        self.subst.insert(var, ty);
        Ok(())
    }
}

fn free_type_vars(ty: &MonoType) -> HashSet<TypeVarId> {
    match ty {
        MonoType::Var(var) => HashSet::from([*var]),
        MonoType::Primitive(_) => HashSet::new(),
        MonoType::Function(params, ret) => {
            let mut vars = HashSet::new();
            for param in params {
                vars.extend(free_type_vars(param));
            }
            vars.extend(free_type_vars(ret));
            vars
        }
    }
}

fn free_type_vars_scheme(scheme: &Scheme) -> HashSet<TypeVarId> {
    let mut vars = free_type_vars(&scheme.ty);
    for quantified in &scheme.vars {
        vars.remove(quantified);
    }
    vars
}

fn instantiate_type(ty: &MonoType, replacements: &HashMap<TypeVarId, MonoType>) -> MonoType {
    match ty {
        MonoType::Var(var) => replacements
            .get(var)
            .cloned()
            .unwrap_or(MonoType::Var(*var)),
        MonoType::Primitive(kind) => MonoType::Primitive(kind.clone()),
        MonoType::Function(params, ret) => MonoType::Function(
            params
                .iter()
                .map(|param| instantiate_type(param, replacements))
                .collect(),
            Box::new(instantiate_type(ret, replacements)),
        ),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn unify_variable_with_primitive() {
        let mut ctx = InferCtx::default();
        let var = ctx.fresh_var();
        let unified = ctx
            .unify(&var, &MonoType::Primitive(PrimitiveType::State))
            .expect("unify succeeds");
        assert_eq!(unified, MonoType::Primitive(PrimitiveType::State));
    }

    #[test]
    fn occurs_check_rejects_recursive_type() {
        let mut ctx = InferCtx::default();
        let var = ctx.fresh_var();
        let recursive = MonoType::Function(
            vec![var.clone()],
            Box::new(MonoType::Primitive(PrimitiveType::Relation)),
        );
        let error = ctx
            .unify(&var, &recursive)
            .expect_err("occurs check must fail");
        assert!(matches!(error, InferenceError::OccursCheckFailed { .. }));
    }

    #[test]
    fn generalize_identity_scheme_quantifies_variable() {
        let mut ctx = InferCtx::default();
        let alpha = ctx.fresh_var();
        let identity = MonoType::Function(vec![alpha.clone()], Box::new(alpha));
        let env = TypeEnv::default();
        let scheme = ctx.generalize(&env, &identity);
        assert_eq!(scheme.vars.len(), 1);
        assert!(matches!(scheme.ty, MonoType::Function(_, _)));
    }

    #[test]
    fn instantiate_generalized_scheme_produces_fresh_variables() {
        let mut ctx = InferCtx::default();
        let scheme = Scheme {
            vars: vec![0],
            ty: MonoType::Function(vec![MonoType::Var(0)], Box::new(MonoType::Var(0))),
        };
        let first = ctx.instantiate(&scheme);
        let second = ctx.instantiate(&scheme);
        assert_ne!(first, second);
    }
}
