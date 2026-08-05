use arkhe_buzz_integration::*;

#[tokio::test]
async fn test_agent_integration() {
    let mut agent = ArkheBuzzAgent::new(8, 1.2, 5.0);
    agent.reentry_step(&[0.1; 8]).unwrap();
    let risk = agent.check_escape();
    assert_eq!(risk, EscapeRisk::High);
}
