---
title: Rustlings - Quizzes
date: 2026-09-17 14:45:46 +0900
categories: [CS, Rust]
---

챕터 중간 중간마다 퀴즈가 하나씩 껴있는것 같다. 이전의 챕터들에서 배웠던 것을 골고루 활용해 볼 수 있다.

## 1. 

```rust
// This is a quiz for the following sections:
// - Variables
// - Functions
// - If
//
// Mary is buying apples. The price of an apple is calculated as follows:
// - An apple costs 2 rustbucks.
// - However, if Mary buys more than 40 apples, the price of each apple in the
// entire order is reduced to only 1 rustbuck!

// TODO: Write a function that calculates the price of an order of apples given
// the quantity bought.
// fn calculate_price_of_apples(???) -> ??? { ??? }
fn main() {
    // You can optionally experiment here.
}

// Don't change the tests!
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn verify_test() {
        assert_eq!(calculate_price_of_apples(35), 70);
        assert_eq!(calculate_price_of_apples(40), 80);
        assert_eq!(calculate_price_of_apples(41), 41);
        assert_eq!(calculate_price_of_apples(65), 65);
    }
}
```

사과의 가격을 계산해서 반환하는 함수를 작성하면 된다.
40개 보다 많은 사과를 사면 그 개수가 곧 가격이다.
그렇지 않다면 그 개수의 2배가 곧 가격이다.

```rust
fn calculate_price_of_apples(num : i32) -> i32{
    if num <= 40 {
        num * 2
    } else {
        num
    }
}
```

## 2. 

## 3. 